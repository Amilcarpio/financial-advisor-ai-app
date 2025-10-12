"""
Webhook endpoints for external service integrations.

Handles incoming webhooks from:
- HubSpot (contact updates, deal changes)
- Gmail (email notifications via Pub/Sub)
- Google Calendar (event changes)
"""

import hashlib
import hmac
import logging
import base64
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request, HTTPException, Depends, Header
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_session
from app.models.task import Task
from app.models.user import User
from app.services.memory_rules import evaluate_rules_for_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# In-memory store for webhook replay protection (use Redis in production)
_processed_webhook_ids: set[str] = set()
_MAX_WEBHOOK_IDS = 10000  # Prevent memory leak


def verify_hubspot_signature(
    request_body: bytes,
    signature: Optional[str],
    client_secret: str
) -> bool:
    """
    Verify HubSpot webhook signature.
    
    HubSpot signs requests with HMAC-SHA256 using the client secret.
    Format: sha256={hash}
    """
    if not signature:
        return False
    
    if not signature.startswith("sha256="):
        return False
    
    expected_signature = signature[7:]  # Remove 'sha256=' prefix
    
    # Compute HMAC-SHA256
    computed_signature = hmac.new(
        client_secret.encode("utf-8"),
        request_body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(computed_signature, expected_signature)


def is_webhook_processed(webhook_id: str) -> bool:
    """Check if webhook has already been processed (replay protection)."""
    return webhook_id in _processed_webhook_ids


def mark_webhook_processed(webhook_id: str) -> None:
    """Mark webhook as processed."""
    _processed_webhook_ids.add(webhook_id)
    
    # Prevent memory leak by removing oldest entries
    if len(_processed_webhook_ids) > _MAX_WEBHOOK_IDS:
        # Remove 10% of oldest entries (simple cleanup strategy)
        to_remove = list(_processed_webhook_ids)[:1000]
        for wid in to_remove:
            _processed_webhook_ids.discard(wid)


@router.post("/hubspot")
async def hubspot_webhook(
    request: Request,
    db: Session = Depends(get_session),
    x_hubspot_signature: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Handle HubSpot webhooks.
    
    Supports:
    - contact.creation
    - contact.propertyChange
    - contact.deletion
    - deal.propertyChange
    
    Requires signature verification for security.
    """
    body_bytes = await request.body()
    
    # Verify signature
    if not settings.hubspot_client_secret:
        logger.warning("HubSpot webhook received but hubspot_client_secret not configured")
        raise HTTPException(status_code=500, detail="Webhook verification not configured")
    
    if not verify_hubspot_signature(
        body_bytes,
        x_hubspot_signature,
        settings.hubspot_client_secret
    ):
        logger.warning("HubSpot webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse webhook payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse HubSpot webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Validate payload structure
    if not isinstance(payload, list):
        logger.error(f"HubSpot webhook payload not a list: {type(payload)}")
        raise HTTPException(status_code=400, detail="Expected array of events")
    
    processed_count = 0
    
    for event in payload:
        # Extract event details
        event_id = event.get("eventId")
        subscription_type = event.get("subscriptionType")
        object_id = event.get("objectId")
        
        if not event_id:
            logger.warning("HubSpot webhook event missing eventId, skipping")
            continue
        
        # Replay protection
        if is_webhook_processed(event_id):
            logger.info(f"HubSpot webhook {event_id} already processed, skipping")
            continue
        
        mark_webhook_processed(event_id)
        
        # Find user by HubSpot portal ID (stored in hubspot_oauth_tokens)
        # For MVP, we'll just use the first user with HubSpot connected
        # In production, store portal_id in User model
        user = db.scalars(
            select(User).where(User.hubspot_oauth_tokens != None)  # type: ignore
        ).first()
        
        if not user:
            logger.warning(f"No user found with HubSpot connected for event {event_id}")
            continue
        
        logger.info(
            f"Processing HubSpot webhook: eventId={event_id}, "
            f"type={subscription_type}, objectId={object_id}"
        )
        
        # Evaluate memory rules
        try:
            await evaluate_rules_for_event(
                db=db,
                user=user,
                event_type=f"hubspot.{subscription_type}",
                event_data=event
            )
            processed_count += 1
        except Exception as e:
            logger.error(f"Failed to evaluate rules for HubSpot event {event_id}: {e}")
            # Continue processing other events
    
    return {
        "status": "ok",
        "processed": processed_count,
        "total": len(payload)
    }


@router.post("/gmail")
async def gmail_webhook(
    request: Request,
    db: Session = Depends(get_session)
) -> Dict[str, Any]:
    """
    Handle Gmail Pub/Sub webhook notifications.
    
    Gmail sends notifications when:
    - New email received
    - Email modified
    - Label changed
    
    Note: Gmail uses Pub/Sub push notifications, which require:
    1. Cloud Pub/Sub topic configured
    2. Push subscription to this endpoint
    3. OAuth consent for gmail.modify scope
    """
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse Gmail webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Gmail Pub/Sub format: {"message": {"data": "...", "messageId": "..."}}
    message = payload.get("message", {})
    message_id = message.get("messageId")
    
    if not message_id:
        logger.error("Gmail webhook missing messageId")
        raise HTTPException(status_code=400, detail="Missing messageId")
    
    # Replay protection
    if is_webhook_processed(message_id):
        logger.info(f"Gmail webhook {message_id} already processed")
        return {"status": "ok", "processed": False}
    
    mark_webhook_processed(message_id)
    
    # Extract email address from data (base64 encoded)
    # Format: {"emailAddress": "user@example.com", "historyId": "..."}
    try:
        data_bytes = base64.b64decode(message.get("data", ""))
        data = json.loads(data_bytes.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to decode Gmail webhook data: {e}")
        raise HTTPException(status_code=400, detail="Invalid message data")
    
    email_address = data.get("emailAddress")
    history_id = data.get("historyId")
    
    if not email_address:
        logger.error("Gmail webhook missing emailAddress")
        raise HTTPException(status_code=400, detail="Missing emailAddress")
    
    # Find user by email
    user = db.scalars(select(User).where(User.email == email_address)).first()
    
    if not user:
        logger.warning(f"No user found for Gmail webhook: {email_address}")
        return {"status": "ok", "processed": False}
    
    logger.info(f"Processing Gmail webhook for {email_address}, historyId={history_id}")
    
    # Create task to sync new messages
    task = Task(
        user_id=user.id,
        task_type="gmail_sync",
        payload={
            "history_id": history_id,
            "email_address": email_address
        },
        state="pending",
        priority=1,
        max_attempts=3
    )
    db.add(task)
    db.commit()
    
    return {
        "status": "ok",
        "processed": True,
        "task_id": task.id
    }


@router.post("/calendar")
async def calendar_webhook(
    request: Request,
    db: Session = Depends(get_session),
    x_goog_channel_id: Optional[str] = Header(None),
    x_goog_resource_state: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Handle Google Calendar webhook notifications.
    
    Calendar sends notifications when:
    - Event created
    - Event updated
    - Event deleted
    
    Requires:
    1. Calendar API watch() call to set up push notifications
    2. Verified domain ownership
    3. OAuth consent for calendar scope
    """
    if not x_goog_channel_id or not x_goog_resource_state:
        logger.error("Calendar webhook missing required headers")
        raise HTTPException(status_code=400, detail="Missing required headers")
    
    # Handle sync message (first message after watch() setup)
    if x_goog_resource_state == "sync":
        logger.info(f"Calendar webhook sync message received: {x_goog_channel_id}")
        return {"status": "ok", "sync": True}
    
    # Get resource URI from header
    x_goog_resource_uri = request.headers.get("X-Goog-Resource-URI")
    x_goog_resource_id = request.headers.get("X-Goog-Resource-ID")
    
    logger.info(
        f"Processing Calendar webhook: channel={x_goog_channel_id}, "
        f"state={x_goog_resource_state}, resource={x_goog_resource_id}"
    )
    
    # For MVP, we'll trigger a full calendar sync for all users
    # In production, store channel_id -> user mapping
    users = db.scalars(
        select(User).where(User.google_oauth_tokens != None)  # type: ignore
    ).all()
    
    tasks_created = 0
    for user in users:
        # Create task to sync calendar
        task = Task(
            user_id=user.id,
            task_type="calendar_sync",
            payload={
                "channel_id": x_goog_channel_id,
                "resource_state": x_goog_resource_state,
                "resource_id": x_goog_resource_id
            },
            state="pending",
            priority=2,
            max_attempts=3
        )
        db.add(task)
        tasks_created += 1
    
    db.commit()
    
    return {
        "status": "ok",
        "tasks_created": tasks_created
    }


@router.get("/health")
async def webhook_health() -> Dict[str, Any]:
    """Health check for webhook endpoints."""
    return {
        "status": "healthy",
        "webhooks": ["hubspot", "gmail", "calendar"],
        "replay_protection": {
            "processed_count": len(_processed_webhook_ids),
            "max_capacity": _MAX_WEBHOOK_IDS
        }
    }
