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
    Verify HubSpot webhook signature per official documentation.
    
    HubSpot v3 webhooks signature verification:
    1. Concatenate client_secret + request_body
    2. Compute SHA-256 hash
    3. Compare with signature header (format: "sha256={hash}")
    
    Reference: https://developers.hubspot.com/docs/api/webhooks
    """
    if not signature:
        return False
    
    if not signature.startswith("sha256="):
        return False
    
    expected_signature = signature[7:]  # Remove 'sha256=' prefix
    
    # Concatenate client_secret + request_body (per HubSpot docs)
    source_string = client_secret.encode("utf-8") + request_body

    # Compute SHA-256 hash
    computed_signature = hashlib.sha256(source_string).hexdigest()

    if hmac.compare_digest(computed_signature, expected_signature):
        return True

    # Detailed debug logging to help diagnose signature mismatches
    try:
        body_preview = request_body[:512].decode("utf-8", errors="replace")
    except Exception:
        body_preview = str(request_body[:512])

    logger.debug(
        "HubSpot signature mismatch: expected=%s computed=%s body_preview=%s",
        expected_signature[:16],
        computed_signature[:16],
        body_preview.replace('\n', '\\n')
    )

    return False


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
    Handle HubSpot v3 webhooks.
    
    Official Documentation: https://developers.hubspot.com/docs/api/webhooks
    
    Supported event types:
    - contact.creation, contact.propertyChange, contact.deletion, contact.merge,
      contact.associationChange, contact.restore, contact.privacyDeletion
    - company.*, deal.*, ticket.*, product.*, line_item.*, conversation.*
    
    Request Format:
        POST /webhooks/hubspot
        Headers:
            X-HubSpot-Signature: sha256={hash}
        Body: Array of event objects
    
    Signature Verification:
        Signature = SHA256(client_secret + request_body)
        Format: "sha256={hex_digest}"
    
    Event Object Fields:
        - eventId: Unique event identifier (not guaranteed unique)
        - subscriptionId: Which subscription triggered this event
        - subscriptionType: Event type (e.g., "contact.creation")
        - portalId: Customer's HubSpot account ID
        - appId: Application ID
        - occurredAt: Timestamp in milliseconds since epoch
        - attemptNumber: Retry attempt number (starts at 0)
        - objectId: ID of the affected CRM object
        - changeSource: Source of the change
        - propertyName: (propertyChange events only)
        - propertyValue: (propertyChange events only)
    
    Retry Behavior:
        - Up to 10 retry attempts over 24 hours
        - Retries on: connection failed, timeout (>5s), any 4xx/5xx response
        - Randomized delays to prevent thundering herd
    
    Batching:
        - Can receive up to 100 events per request
    
    Returns:
        JSON object with processing status
    """
    try:
        body_bytes = await request.body()
    except Exception as e:
        # ClientDisconnect and other stream errors can raise while reading body
        logger.warning(f"Failed to read webhook body: {e}")
        raise HTTPException(status_code=400, detail="Failed to read request body")

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
        # Extract event details per HubSpot v3 webhook documentation
        # Reference: https://developers.hubspot.com/docs/api/webhooks
        event_id = event.get("eventId")
        subscription_type = event.get("subscriptionType")
        object_id = event.get("objectId")
        portal_id = event.get("portalId")
        app_id = event.get("appId")
        occurred_at = event.get("occurredAt")
        attempt_number = event.get("attemptNumber", 0)
        change_source = event.get("changeSource")
        
        if not event_id:
            logger.warning("HubSpot webhook event missing eventId, skipping")
            continue
        
        # Replay protection
        if is_webhook_processed(event_id):
            logger.info(f"HubSpot webhook {event_id} already processed, skipping")
            continue
        
        mark_webhook_processed(event_id)
        
        # Find user by HubSpot portal ID (preferred method)
        user = None
        if portal_id:
            user = db.scalars(
                select(User).where(User.hubspot_portal_id == str(portal_id))
            ).first()
        
        # Fallback: find first user with HubSpot connected (for backward compatibility)
        if not user:
            logger.warning(f"No user found with portal_id={portal_id}, using fallback")
            user = db.scalars(
                select(User).where(User.hubspot_oauth_tokens != None)  # type: ignore
            ).first()
        
        if not user:
            logger.warning(f"No user found for HubSpot webhook event {event_id}")
            continue
        
        logger.info(
            f"Processing HubSpot webhook: eventId={event_id}, "
            f"type={subscription_type}, objectId={object_id}, "
            f"portalId={portal_id}, attemptNumber={attempt_number}"
        )
        
        # Evaluate memory rules with complete event data
        try:
            await evaluate_rules_for_event(
                db=db,
                user=user,
                event_type=f"hubspot.{subscription_type}",
                event_data=event  # Pass complete event with all fields
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
    Handle Gmail Pub/Sub push notifications.
    
    Official Documentation: https://developers.google.com/gmail/api/guides/push
    
    Gmail sends notifications when:
    - New email received
    - Email modified
    - Label changed
    
    Request Format:
        POST /webhooks/gmail
        Headers:
            Content-Type: application/json
        Body:
            {
              "message": {
                "data": "base64url-encoded-json-string",
                "messageId": "2070443601311540",
                "publishTime": "2021-02-26T19:13:55.749Z"
              },
              "subscription": "projects/myproject/subscriptions/mysubscription"
            }
    
    Decoded message.data format:
        {
          "emailAddress": "user@example.com",
          "historyId": "9876543210"
        }
    
    Setup Requirements:
    1. Cloud Pub/Sub topic configured
    2. Push subscription pointing to this endpoint
    3. OAuth consent for gmail.modify scope
    4. watch() API call to enable notifications (expires after 7 days)
    
    Rate Limits:
    - Max 1 notification/second per user
    - Notifications may be delayed or dropped in extreme situations
    - Implement fallback polling with history.list
    
    Returns:
        JSON object with processing status
    """
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse Gmail webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Gmail Pub/Sub format: {"message": {"data": "...", "messageId": "...", "publishTime": "..."}}
    message = payload.get("message", {})
    message_id = message.get("messageId")
    publish_time = message.get("publishTime")
    subscription = payload.get("subscription")
    
    if not message_id:
        logger.error("Gmail webhook missing messageId")
        raise HTTPException(status_code=400, detail="Missing messageId")
    
    # Replay protection
    if is_webhook_processed(message_id):
        logger.info(f"Gmail webhook {message_id} already processed")
        return {"status": "ok", "processed": False}
    
    mark_webhook_processed(message_id)
    
    # Extract email address from data (base64url encoded JSON per Google Pub/Sub spec)
    # Format: {"emailAddress": "user@example.com", "historyId": "..."}
    try:
        # Gmail uses standard base64 encoding (not URL-safe) in practice
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
    
    logger.info(
        f"Processing Gmail webhook for {email_address}, "
        f"historyId={history_id}, messageId={message_id}, "
        f"publishTime={publish_time}"
    )
    
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
    Handle Google Calendar push notifications.
    
    Official Documentation: https://developers.google.com/calendar/api/guides/push
    
    Calendar sends notifications when:
    - Event created
    - Event updated
    - Event deleted
    
    Request Headers:
        X-Goog-Channel-ID: UUID identifying the notification channel
        X-Goog-Channel-Token: Optional verification token
        X-Goog-Resource-ID: Opaque ID of watched resource
        X-Goog-Resource-URI: URI of watched resource
        X-Goog-Resource-State: Current state of resource
        X-Goog-Message-Number: Sequential message number
    
    Resource States:
        - sync: First notification after watch() setup (no action needed)
        - exists: Resource exists and has content
        - not_exists: Resource was deleted
    
    Setup Requirements:
    1. Calendar API watch() call to set up push notifications
    2. Verified domain ownership
    3. OAuth consent for calendar scope
    4. HTTPS endpoint (no localhost in production)
    
    Channel Expiration:
    - Channels expire after specified time or max 1 week
    - Must renew with watch() before expiration
    - Stop notifications with stop() method
    
    Note: Current implementation syncs all users with Calendar connected.
          Production should store channel_id -> user_id mapping for efficiency.
    
    Returns:
        JSON object with processing status
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
