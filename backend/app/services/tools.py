"""
Tools for AI agent actions: Gmail, Calendar, HubSpot, and Tasks.

This module provides safe wrappers for external actions with:
- Email sending via Gmail API
- Calendar event scheduling via Google Calendar API
- Contact management via HubSpot API
- Internal task creation

All tools include validation, error handling, and action logging.
"""

from datetime import datetime
from typing import Any, Optional
import json
import base64
import logging
import re
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.user import User
from app.models.task import Task
from app.core.config import settings


logger = logging.getLogger(__name__)


async def _sync_calendar_event_to_vector_store(
    event_id: str,
    user: User,
    db: Session,
    event_data: Optional[dict[str, Any]] = None,
    delete: bool = False,
) -> None:
    """
    Synchronize a calendar event with the vector store.
    
    Args:
        event_id: Google Calendar event ID
        user: User who owns the event
        db: Database session
        event_data: Event data from Google Calendar (required if not deleting)
        delete: If True, removes from vector store. If False, adds/updates.
    """
    from app.models.vector_item import VectorItem
    from app.services.embeddings import EmbeddingService
    
    try:
        if delete:
            # Remove from vector store
            deleted_count = db.query(VectorItem).filter(
                VectorItem.user_id == user.id,
                VectorItem.source_type == "calendar",
                VectorItem.source_id == event_id
            ).delete()
            db.commit()
            
            if deleted_count > 0:
                logger.info(f"Removed {deleted_count} calendar event(s) from vector store for event {event_id}")
        else:
            if not event_data:
                logger.warning(f"Cannot sync calendar event {event_id} without event_data")
                return
            
            # Format event for embedding
            summary = event_data.get('summary', 'Untitled Event')
            start = event_data.get('start', {})
            end = event_data.get('end', {})
            description = event_data.get('description', '')
            location = event_data.get('location', '')
            attendees = event_data.get('attendees', [])
            
            # Build text representation
            text_parts = [f"Event: {summary}"]
            
            if start.get('dateTime'):
                text_parts.append(f"Start: {start['dateTime']}")
            elif start.get('date'):
                text_parts.append(f"Date: {start['date']}")
            
            if end.get('dateTime'):
                text_parts.append(f"End: {end['dateTime']}")
            elif end.get('date'):
                text_parts.append(f"End Date: {end['date']}")
            
            if location:
                text_parts.append(f"Location: {location}")
            
            if description:
                text_parts.append(f"Description: {description}")
            
            if attendees:
                attendee_emails = [a.get('email', '') for a in attendees if a.get('email')]
                if attendee_emails:
                    text_parts.append(f"Attendees: {', '.join(attendee_emails)}")
            
            text_parts.append(f"Event ID: {event_id}")
            
            text = "\n".join(text_parts)
            
            # Generate embedding
            embedding_service = EmbeddingService()
            embedding = embedding_service.embed_text(text)
            
            # Check if already exists
            existing = db.query(VectorItem).filter(
                VectorItem.user_id == user.id,
                VectorItem.source_type == "calendar",
                VectorItem.source_id == event_id
            ).first()
            
            if existing:
                # Update existing
                existing.text = text
                existing.embedding = embedding
                existing.metadata_json = event_data
                existing.touch()
                logger.info(f"Updated calendar event {event_id} in vector store")
            else:
                # Create new
                vector_item = VectorItem(
                    user_id=user.id,
                    source_type="calendar",
                    source_id=event_id,
                    text=text,
                    embedding=embedding,
                    metadata_json=event_data,
                )
                db.add(vector_item)
                logger.info(f"Added calendar event {event_id} to vector store")
            
            db.commit()
            
    except Exception as e:
        logger.error(f"Failed to sync calendar event {event_id} to vector store: {e}")
        db.rollback()


# WARNING: In-memory rate limiting does NOT work in production with load balancers
# or multiple server instances. Use Redis with a sliding window algorithm instead.
# Example: redis.incr(f"email_rate:{user_id}:{hour}", expire=3600)
_email_rate_limits: dict[int, list[datetime]] = {}
MAX_EMAILS_PER_HOUR = 50
MAX_EMAILS_GLOBAL_PER_HOUR = 500


class ToolExecutionError(Exception):
    """Raised when a tool execution fails."""
    pass


class HubSpotTokenExpiredError(ToolExecutionError):
    """Exception raised when HubSpot OAuth token is expired or invalid."""
    def __init__(self, message: str = "HubSpot authentication expired. Please reconnect your HubSpot account."):
        self.message = message
        super().__init__(self.message)


def _get_google_credentials(user: User) -> Credentials:
    """
    Build Google OAuth credentials from user tokens.
    
    Args:
        user: User with google_oauth_tokens
        
    Returns:
        Google Credentials object
        
    Raises:
        ToolExecutionError: If tokens are missing or invalid
    """
    if not user.google_oauth_tokens:
        raise ToolExecutionError("Google OAuth tokens not found. Please connect your Google account.")
    
    try:
        token_data = json.loads(user.google_oauth_tokens) if isinstance(user.google_oauth_tokens, str) else user.google_oauth_tokens
        
        credentials = Credentials(
            token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=token_data.get("scopes", []),
        )
        
        return credentials
        
    except Exception as e:
        raise ToolExecutionError(f"Failed to build Google credentials: {str(e)}")


def _check_email_rate_limit(user_id: int) -> tuple[bool, str]:
    """
    Check if user is within email rate limits.
    
    Args:
        user_id: User ID to check
        
    Returns:
        Tuple of (is_allowed, error_message)
    """
    now = datetime.utcnow()
    one_hour_ago = datetime.utcnow().timestamp() - 3600
    
    # Initialize user's rate limit tracking
    if user_id not in _email_rate_limits:
        _email_rate_limits[user_id] = []
    
    # Clean old timestamps
    _email_rate_limits[user_id] = [
        ts for ts in _email_rate_limits[user_id]
        if ts.timestamp() > one_hour_ago
    ]
    
    # Check user limit
    if len(_email_rate_limits[user_id]) >= MAX_EMAILS_PER_HOUR:
        return False, f"Rate limit exceeded: maximum {MAX_EMAILS_PER_HOUR} emails per hour"
    
    # Check global limit
    total_emails = sum(len(timestamps) for timestamps in _email_rate_limits.values())
    if total_emails >= MAX_EMAILS_GLOBAL_PER_HOUR:
        return False, "System rate limit exceeded. Please try again later."
    
    return True, ""


def _record_email_sent(user_id: int) -> None:
    """Record that an email was sent for rate limiting."""
    if user_id not in _email_rate_limits:
        _email_rate_limits[user_id] = []
    _email_rate_limits[user_id].append(datetime.utcnow())


async def send_email(
    user: User,
    to: list[str],
    subject: str,
    body: str,
    cc: Optional[list[str]] = None,
    bcc: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Send an email via Gmail API.
    
    Args:
        user: User sending the email
        to: List of recipient email addresses
        subject: Email subject
        body: Email body (plain text or HTML)
        cc: Optional list of CC addresses
        bcc: Optional list of BCC addresses
        
    Returns:
        Dict with messageId and status
        
    Raises:
        ToolExecutionError: If sending fails
    """
    # Check rate limits
    is_allowed, error_msg = _check_email_rate_limit(user.id or 0)
    if not is_allowed:
        raise ToolExecutionError(error_msg)
    
    try:
        # Get credentials
        credentials = _get_google_credentials(user)
        
        # Build Gmail service
        service = build('gmail', 'v1', credentials=credentials)
        
        # Create message
        message = MIMEText(body)
        message['to'] = ', '.join(to)
        message['subject'] = subject
        
        if cc:
            message['cc'] = ', '.join(cc)
        if bcc:
            message['bcc'] = ', '.join(bcc)
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send message
        result = service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        # Record for rate limiting
        _record_email_sent(user.id or 0)
        
        return {
            "status": "success",
            "message_id": result.get('id'),
            "thread_id": result.get('threadId'),
            "recipients": to,
        }
        
    except HttpError as e:
        error_details = e.error_details if hasattr(e, 'error_details') else str(e)
        raise ToolExecutionError(f"Gmail API error: {error_details}")
    except Exception as e:
        raise ToolExecutionError(f"Failed to send email: {str(e)}")


async def schedule_event(
    user: User,
    summary: str,
    start_time: str,
    end_time: str,
    description: Optional[str] = None,
    attendees: Optional[list[str]] = None,
    location: Optional[str] = None,
    db: Optional[Session] = None,
) -> dict[str, Any]:
    """
    Schedule a calendar event via Google Calendar API.
    
    Args:
        user: User creating the event
        summary: Event title
        start_time: Start time in ISO 8601 format
        end_time: End time in ISO 8601 format
        description: Optional event description
        attendees: Optional list of attendee email addresses
        location: Optional event location
        db: Database session for syncing to vector store
        
    Returns:
        Dict with event details and link
        
    Raises:
        ToolExecutionError: If scheduling fails
    """
    try:
        # Get credentials
        credentials = _get_google_credentials(user)
        
        # Build Calendar service
        service = build('calendar', 'v3', credentials=credentials)
        
        # Build event
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time,
                'timeZone': 'America/Denver',  # Default timezone
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'America/Denver',
            },
        }
        
        if description:
            event['description'] = description
        
        if location:
            event['location'] = location
        
        if attendees:
            event['attendees'] = [{'email': email} for email in attendees]
            event['sendUpdates'] = 'all'  # Send invitations
        
        # Create event
        result = service.events().insert(
            calendarId='primary',
            body=event,
            sendUpdates='all' if attendees else 'none'
        ).execute()
        
        # Sync to vector store
        if db:
            await _sync_calendar_event_to_vector_store(
                event_id=result.get('id'),
                user=user,
                db=db,
                event_data=result,
                delete=False,
            )
        
        return {
            "status": "success",
            "event_id": result.get('id'),
            "event_link": result.get('htmlLink'),
            "summary": result.get('summary'),
            "start": result.get('start', {}).get('dateTime'),
            "end": result.get('end', {}).get('dateTime'),
            "attendees": attendees or [],
            "event": result,  # Return full event data
        }
        
    except HttpError as e:
        error_details = e.error_details if hasattr(e, 'error_details') else str(e)
        raise ToolExecutionError(f"Calendar API error: {error_details}")
    except Exception as e:
        raise ToolExecutionError(f"Failed to schedule event: {str(e)}")


async def update_event(
    user: User,
    event_id: str,
    summary: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    description: Optional[str] = None,
    attendees: Optional[list[str]] = None,
    location: Optional[str] = None,
    db: Optional[Session] = None,
) -> dict[str, Any]:
    """
    Update an existing calendar event via Google Calendar API.
    
    Args:
        user: User updating the event
        event_id: Google Calendar event ID to update
        summary: Optional new event title
        start_time: Optional new start time in ISO 8601 format
        end_time: Optional new end time in ISO 8601 format
        description: Optional new event description
        attendees: Optional new list of attendee email addresses
        location: Optional new event location
        db: Database session for syncing to vector store
        
    Returns:
        Dict with updated event details
        
    Raises:
        ToolExecutionError: If update fails
    """
    try:
        # Get credentials
        credentials = _get_google_credentials(user)
        
        # Build Calendar service
        service = build('calendar', 'v3', credentials=credentials)
        
        # Fetch current event
        current_event = service.events().get(
            calendarId='primary',
            eventId=event_id
        ).execute()
        
        # Update only provided fields
        if summary is not None:
            current_event['summary'] = summary
        
        if start_time is not None:
            current_event['start'] = {
                'dateTime': start_time,
                'timeZone': 'America/Denver',
            }
        
        if end_time is not None:
            current_event['end'] = {
                'dateTime': end_time,
                'timeZone': 'America/Denver',
            }
        
        if description is not None:
            current_event['description'] = description
        
        if location is not None:
            current_event['location'] = location
        
        if attendees is not None:
            current_event['attendees'] = [{'email': email} for email in attendees]
            current_event['sendUpdates'] = 'all'
        
        # Update event
        result = service.events().update(
            calendarId='primary',
            eventId=event_id,
            body=current_event,
            sendUpdates='all' if attendees is not None else 'none'
        ).execute()
        
        # Sync to vector store
        if db:
            await _sync_calendar_event_to_vector_store(
                event_id=result.get('id'),
                user=user,
                db=db,
                event_data=result,
                delete=False,
            )
        
        return {
            "status": "success",
            "event_id": result.get('id'),
            "event_link": result.get('htmlLink'),
            "summary": result.get('summary'),
            "start": result.get('start', {}).get('dateTime'),
            "end": result.get('end', {}).get('dateTime'),
            "updated_at": result.get('updated'),
            "event": result,  # Return full event data
        }
        
    except HttpError as e:
        error_details = e.error_details if hasattr(e, 'error_details') else str(e)
        raise ToolExecutionError(f"Calendar API error: {error_details}")
    except Exception as e:
        raise ToolExecutionError(f"Failed to update event: {str(e)}")


async def cancel_event(
    user: User,
    event_id: str,
    send_updates: bool = True,
    db: Optional[Session] = None,
) -> dict[str, Any]:
    """
    Cancel (delete) a calendar event via Google Calendar API.
    
    Args:
        user: User canceling the event
        event_id: Google Calendar event ID to cancel
        send_updates: Whether to send cancellation notifications to attendees
        db: Database session for removing from vector store
        
    Returns:
        Dict with cancellation status
        
    Raises:
        ToolExecutionError: If cancellation fails
    """
    try:
        # Get credentials
        credentials = _get_google_credentials(user)
        
        # Build Calendar service
        service = build('calendar', 'v3', credentials=credentials)
        
        # Delete event
        service.events().delete(
            calendarId='primary',
            eventId=event_id,
            sendUpdates='all' if send_updates else 'none'
        ).execute()
        
        logger.info(f"Deleted calendar event {event_id} from Google Calendar")
        
        if db:
            await _sync_calendar_event_to_vector_store(
                event_id=event_id,
                user=user,
                db=db,
                delete=True,
            )
        
        return {
            "status": "success",
            "event_id": event_id,
            "message": "Event cancelled successfully",
        }
        
    except HttpError as e:
        error_details = e.error_details if hasattr(e, 'error_details') else str(e)
        raise ToolExecutionError(f"Calendar API error: {error_details}")
    except Exception as e:
        raise ToolExecutionError(f"Failed to cancel event: {str(e)}")


async def find_contact(
    user: User,
    query: str,
    limit: int = 5,
) -> dict[str, Any]:
    """
    Search for contacts in HubSpot CRM.
    
    Args:
        user: User performing the search
        query: Search query (name, email, or company)
        limit: Maximum number of results (must be between 1 and 100)
        
    Returns:
        Dict with list of matching contacts
        
    Raises:
        ToolExecutionError: If search fails
    """
    if not user.hubspot_oauth_tokens:
        raise ToolExecutionError("HubSpot OAuth tokens not found. Please connect your HubSpot account.")
    
    # Validate limit
    if limit < 1 or limit > 100:
        raise ToolExecutionError("Limit must be between 1 and 100")
    
    try:
        # Get access token
        token_data = json.loads(user.hubspot_oauth_tokens) if isinstance(user.hubspot_oauth_tokens, str) else user.hubspot_oauth_tokens
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise ToolExecutionError("HubSpot access token not found")
        
        # Detect if query looks like "First Last" (full name)
        filter_groups = []
        query_parts = query.strip().split()
        
        # If query has exactly 2 words, try firstname AND lastname match
        if len(query_parts) == 2:
            filter_groups.append({
                "filters": [
                    {
                        "propertyName": "firstname",
                        "operator": "CONTAINS_TOKEN",
                        "value": query_parts[0],
                    },
                    {
                        "propertyName": "lastname",
                        "operator": "CONTAINS_TOKEN",
                        "value": query_parts[1],
                    },
                ]
            })
        
        # Also add OR filters (original logic) - this becomes an OR with the AND above
        filter_groups.append({
            "filters": [
                {
                    "propertyName": "email",
                    "operator": "CONTAINS_TOKEN",
                    "value": query,
                },
                {
                    "propertyName": "firstname",
                    "operator": "CONTAINS_TOKEN",
                    "value": query,
                },
                {
                    "propertyName": "lastname",
                    "operator": "CONTAINS_TOKEN",
                    "value": query,
                },
                {
                    "propertyName": "company",
                    "operator": "CONTAINS_TOKEN",
                    "value": query,
                },
            ]
        })
        
        logger.info(f"[find_contact] Searching HubSpot for: '{query}' (detected {len(query_parts)} parts)")
        
        # Search contacts via HubSpot API
        async with httpx.AsyncClient() as client:
            search_payload = {
                "filterGroups": filter_groups,
                "properties": ["firstname", "lastname", "email", "phone", "company"],
                "limit": limit,
            }
            
            logger.debug(f"[find_contact] HubSpot search payload: {json.dumps(search_payload, indent=2)}")
            
            response = await client.post(
                "https://api.hubapi.com/crm/v3/objects/contacts/search",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json=search_payload,
                timeout=30.0,
            )
            
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"[find_contact] HubSpot returned {len(data.get('results', []))} results")
            
            contacts = []
            for result in data.get("results", []):
                props = result.get("properties", {})
                contact = {
                    "id": result.get("id"),
                    "first_name": props.get("firstname"),
                    "last_name": props.get("lastname"),
                    "email": props.get("email"),
                    "phone": props.get("phone"),
                    "company": props.get("company"),
                }
                contacts.append(contact)
                logger.debug(f"[find_contact] Found: {contact}")
            
            return {
                "status": "success",
                "total": len(contacts),
                "contacts": contacts,
            }
            
    except httpx.HTTPStatusError as e:
        # Check if it's an authentication error
        if e.response.status_code == 401:
            logger.warning(f"HubSpot token expired for user {user.id}: {e.response.text}")
            raise HubSpotTokenExpiredError()
        raise ToolExecutionError(f"HubSpot API error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise ToolExecutionError(f"Failed to search contacts: {str(e)}")


async def create_contact(
    user: User,
    email: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    notes: Optional[str] = None,
    job_title: Optional[str] = None,
    website: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
    country: Optional[str] = None,
    lifecycle_stage: Optional[str] = None,
) -> dict[str, Any]:
    """
    Create a new contact in HubSpot CRM.
    
    Args:
        user: User creating the contact
        email: Contact email (required)
        first_name: Contact first name
        last_name: Contact last name
        phone: Contact phone number
        company: Contact company
        notes: Additional notes (will create a note engagement)
        job_title: Contact job title
        website: Contact website
        city: Contact city
        state: Contact state/region
        zip_code: Contact postal code
        country: Contact country
        lifecycle_stage: Lifecycle stage (subscriber, lead, marketingqualifiedlead, 
                        salesqualifiedlead, opportunity, customer, evangelist, other)
        
    Returns:
        Dict with created contact details
        
    Raises:
        ToolExecutionError: If creation fails
    """
    if not user.hubspot_oauth_tokens:
        raise ToolExecutionError("HubSpot OAuth tokens not found. Please connect your HubSpot account.")
    
    try:
        # Get access token
        token_data = json.loads(user.hubspot_oauth_tokens) if isinstance(user.hubspot_oauth_tokens, str) else user.hubspot_oauth_tokens
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise ToolExecutionError("HubSpot access token not found")
        
        # Build properties
        properties: dict[str, str] = {"email": email}
        
        if first_name:
            properties["firstname"] = first_name
        if last_name:
            properties["lastname"] = last_name
        if phone:
            properties["phone"] = phone
        if company:
            properties["company"] = company
        if job_title:
            properties["jobtitle"] = job_title
        if website:
            properties["website"] = website
        if city:
            properties["city"] = city
        if state:
            properties["state"] = state
        if zip_code:
            properties["zip"] = zip_code
        if country:
            properties["country"] = country
        if lifecycle_stage:
            properties["lifecyclestage"] = lifecycle_stage
        # Note: 'notes' field removed - HubSpot doesn't have a default notes property
        # Notes should be added as a separate note/engagement if needed
        
        # Create contact via HubSpot API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.hubapi.com/crm/v3/objects/contacts",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"properties": properties},
                timeout=30.0,
            )
            
            # Handle duplicate contact (409)
            if response.status_code == 409:
                logger.info(f"[create_contact] Contact exists (409): {response.text}")
                
                # Try to extract ID from error message (HubSpot sometimes returns it)
                error_data = response.json() if response.text else {}
                error_message = error_data.get("message", "")
                
                # Try regex to extract ID from error message like "Contact already exists. Existing ID: 163202512937"
                id_match = re.search(r"ID:\s*(\d+)", error_message)
                if id_match:
                    existing_id = id_match.group(1)
                    logger.info(f"[create_contact] Extracted existing contact ID from error: {existing_id}")
                    
                    # Get full contact details using direct GET by ID
                    get_response = await client.get(
                        f"https://api.hubapi.com/crm/v3/objects/contacts/{existing_id}",
                        headers={"Authorization": f"Bearer {access_token}"},
                        params={"properties": "firstname,lastname,email,phone,company"},
                        timeout=30.0,
                    )
                    
                    if get_response.status_code == 200:
                        contact_data = get_response.json()
                        props = contact_data.get("properties", {})
                        return {
                            "status": "exists",
                            "contact_id": existing_id,
                            "message": "Contact with this email already exists",
                            "contact": {
                                "id": existing_id,
                                "first_name": props.get("firstname"),
                                "last_name": props.get("lastname"),
                                "email": props.get("email"),
                                "phone": props.get("phone"),
                                "company": props.get("company"),
                            },
                        }
                
                # Fallback: try to search by email
                search_result = await find_contact(user, email, limit=1)
                if search_result.get("contacts"):
                    existing = search_result["contacts"][0]
                    logger.info(f"[create_contact] Found existing contact via search: {existing}")
                    return {
                        "status": "exists",
                        "contact_id": existing["id"],
                        "message": "Contact with this email already exists",
                        "contact": existing,
                    }
                
                # If we still can't find it, raise the original error
                raise ToolExecutionError(f"Contact already exists but could not retrieve details: {error_message}")
            
            response.raise_for_status()
            data = response.json()
            contact_id = data.get("id")
            
            props = data.get("properties", {})
            result = {
                "status": "success",
                "contact_id": contact_id,
                "email": props.get("email"),
                "first_name": props.get("firstname"),
                "last_name": props.get("lastname"),
                "phone": props.get("phone"),
                "company": props.get("company"),
                "job_title": props.get("jobtitle"),
                "website": props.get("website"),
                "city": props.get("city"),
                "state": props.get("state"),
                "zip": props.get("zip"),
                "country": props.get("country"),
                "lifecycle_stage": props.get("lifecyclestage"),
            }
            
            # If notes provided, create a note engagement
            if notes and contact_id:
                try:
                    note_result = await create_note(user, contact_id, notes)
                    result["note_created"] = True
                    result["note_id"] = note_result.get("note_id")
                except Exception as note_error:
                    logger.warning(f"Failed to create note for contact {contact_id}: {note_error}")
                    result["note_created"] = False
            
            return result
            
    except httpx.HTTPStatusError as e:
        # Check if it's an authentication error
        if e.response.status_code == 401:
            logger.warning(f"HubSpot token expired for user {user.id}: {e.response.text}")
            raise HubSpotTokenExpiredError()
        raise ToolExecutionError(f"HubSpot API error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise ToolExecutionError(f"Failed to create contact: {str(e)}")


async def create_note(
    user: User,
    contact_id: str,
    note_body: str,
) -> dict[str, Any]:
    """
    Create a note and associate it with a HubSpot contact.
    
    Args:
        user: User with HubSpot OAuth credentials
        contact_id: HubSpot contact ID to associate the note with
        note_body: Text content of the note
        
    Returns:
        Dict with note creation result including note_id and status
        
    Raises:
        ToolExecutionError: If note creation fails
    """
    try:
        # Get HubSpot access token
        if not user.hubspot_oauth_tokens:
            raise ToolExecutionError("User is not connected to HubSpot")
        
        access_token = user.hubspot_oauth_tokens.get("access_token")
        if not access_token:
            raise ToolExecutionError("HubSpot access token not found")
        
        # Create note with association to contact
        async with httpx.AsyncClient() as client:
            # Create note
            note_response = await client.post(
                "https://api.hubapi.com/crm/v3/objects/notes",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "properties": {
                        "hs_timestamp": datetime.utcnow().isoformat() + "Z",
                        "hs_note_body": note_body,
                    },
                    "associations": [
                        {
                            "to": {"id": contact_id},
                            "types": [
                                {
                                    "associationCategory": "HUBSPOT_DEFINED",
                                    "associationTypeId": 202  # note_to_contact
                                }
                            ]
                        }
                    ]
                },
                timeout=30.0,
            )
            
            note_response.raise_for_status()
            note_data = note_response.json()
            
            logger.info(
                f"Created note {note_data.get('id')} for contact {contact_id}"
            )
            
            return {
                "status": "success",
                "note_id": note_data.get("id"),
                "contact_id": contact_id,
                "body": note_body,
                "timestamp": note_data.get("properties", {}).get("hs_timestamp"),
            }
            
    except httpx.HTTPStatusError as e:
        # Check if it's an authentication error
        if e.response.status_code == 401:
            logger.warning(f"HubSpot token expired for user {user.id}: {e.response.text}")
            raise HubSpotTokenExpiredError()
        raise ToolExecutionError(
            f"HubSpot API error creating note: {e.response.status_code} - {e.response.text}"
        )
    except Exception as e:
        raise ToolExecutionError(f"Failed to create note: {str(e)}")


async def update_contact(
    user: User,
    contact_id: str,
    email: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    job_title: Optional[str] = None,
    website: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
    country: Optional[str] = None,
    lifecycle_stage: Optional[str] = None,
) -> dict[str, Any]:
    """
    Update an existing contact in HubSpot CRM.
    
    Args:
        user: User updating the contact
        contact_id: HubSpot contact ID to update
        email: Contact email
        first_name: Contact first name
        last_name: Contact last name
        phone: Contact phone number
        company: Contact company
        job_title: Contact job title
        website: Contact website
        city: Contact city
        state: Contact state/region
        zip_code: Contact postal code
        country: Contact country
        lifecycle_stage: Lifecycle stage
        
    Returns:
        Dict with updated contact details
        
    Raises:
        ToolExecutionError: If update fails
    """
    if not user.hubspot_oauth_tokens:
        raise ToolExecutionError("HubSpot OAuth tokens not found. Please connect your HubSpot account.")
    
    try:
        # Get access token
        token_data = json.loads(user.hubspot_oauth_tokens) if isinstance(user.hubspot_oauth_tokens, str) else user.hubspot_oauth_tokens
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise ToolExecutionError("HubSpot access token not found")
        
        # Build properties (only include provided fields)
        properties: dict[str, str] = {}
        
        if email is not None:
            properties["email"] = email
        if first_name is not None:
            properties["firstname"] = first_name
        if last_name is not None:
            properties["lastname"] = last_name
        if phone is not None:
            properties["phone"] = phone
        if company is not None:
            properties["company"] = company
        if job_title is not None:
            properties["jobtitle"] = job_title
        if website is not None:
            properties["website"] = website
        if city is not None:
            properties["city"] = city
        if state is not None:
            properties["state"] = state
        if zip_code is not None:
            properties["zip"] = zip_code
        if country is not None:
            properties["country"] = country
        if lifecycle_stage is not None:
            properties["lifecyclestage"] = lifecycle_stage
        
        if not properties:
            raise ToolExecutionError("No fields provided to update")
        
        # Update contact via HubSpot API
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={"properties": properties},
                timeout=30.0,
            )
            
            response.raise_for_status()
            data = response.json()
            
            props = data.get("properties", {})
            return {
                "status": "success",
                "contact_id": data.get("id"),
                "email": props.get("email"),
                "first_name": props.get("firstname"),
                "last_name": props.get("lastname"),
                "phone": props.get("phone"),
                "company": props.get("company"),
                "job_title": props.get("jobtitle"),
                "website": props.get("website"),
                "city": props.get("city"),
                "state": props.get("state"),
                "zip": props.get("zip"),
                "country": props.get("country"),
                "lifecycle_stage": props.get("lifecyclestage"),
                "updated_fields": list(properties.keys()),
            }
            
    except httpx.HTTPStatusError as e:
        # Check if it's an authentication error
        if e.response.status_code == 401:
            logger.warning(f"HubSpot token expired for user {user.id}: {e.response.text}")
            raise HubSpotTokenExpiredError()
        raise ToolExecutionError(f"HubSpot API error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise ToolExecutionError(f"Failed to update contact: {str(e)}")


async def create_task(
    db: Session,
    user: User,
    task_type: str,
    payload: dict[str, Any],
    scheduled_at: Optional[datetime] = None,
) -> dict[str, Any]:
    """
    Create an internal task for the worker to process.
    
    Args:
        db: Database session
        user: User creating the task
        task_type: Type of task (e.g., 'send_email', 'schedule_event')
        payload: Task payload data
        scheduled_at: Optional scheduled execution time
        
    Returns:
        Dict with task details
    """
    try:
        task = Task(
            user_id=user.id,
            task_type=task_type,
            payload=payload,
            state="pending",
            attempts=0,
            scheduled_for=scheduled_at or datetime.utcnow(),
        )
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        return {
            "status": "success",
            "task_id": task.id,
            "type": task.task_type,
            "state": task.state,
            "scheduled_for": task.scheduled_for.isoformat() if task.scheduled_for else None,
        }
        
    except Exception as e:
        db.rollback()
        raise ToolExecutionError(f"Failed to create task: {str(e)}")


async def create_memory_rule(
    user: User,
    db: Session,
    rule_description: str,
) -> dict[str, Any]:
    """
    Create a persistent memory rule that will be evaluated on future events.
    
    Args:
        user: User creating the rule
        db: Database session
        rule_description: Natural language description of the rule
        
    Returns:
        Dict with rule creation status
    """
    from app.models.memory_rule import MemoryRule
    
    try:
        # Validate input
        if not rule_description or not rule_description.strip():
            raise ToolExecutionError("rule_description cannot be empty")
        
        # Create the rule with the natural language description
        # The rule_text will be the same as description for now
        # A future enhancement could parse this into structured format
        rule = MemoryRule(
            user_id=user.id,
            rule_text=rule_description.strip(),
            is_active=True,  # Active by default
        )
        
        db.add(rule)
        db.commit()
        db.refresh(rule)
        
        return {
            "status": "success",
            "message": f"Memory rule created successfully. I will remember to: {rule_description}",
            "rule_id": rule.id,
            "rule_text": rule.rule_text,
            "is_active": rule.is_active,
        }
        
    except Exception as e:
        db.rollback()
        raise ToolExecutionError(f"Failed to create memory rule: {str(e)}")


async def list_memory_rules(
    user: User,
    db: Session,
) -> dict[str, Any]:
    """
    List all active memory rules for the user.
    
    Args:
        user: User whose rules to list
        db: Database session
        
    Returns:
        Dict with list of memory rules
    """
    from app.models.memory_rule import MemoryRule
    
    try:
        rules = db.query(MemoryRule).filter(
            MemoryRule.user_id == user.id,
            MemoryRule.is_active == True,
        ).order_by(MemoryRule.created_at.desc()).all()
        
        rules_list = []
        for rule in rules:
            rules_list.append({
                "rule_id": rule.id,
                "rule_text": rule.rule_text,
                "created_at": rule.created_at.isoformat() if rule.created_at else None,
            })
        
        return {
            "status": "success",
            "total": len(rules_list),
            "rules": rules_list,
        }
        
    except Exception as e:
        raise ToolExecutionError(f"Failed to list memory rules: {str(e)}")


async def search_emails(
    user: User,
    db: Session,
    query: str,
    date_filter: Optional[str] = None,
    sender_filter: Optional[str] = None,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Search through synced Gmail emails.
    
    Args:
        user: User performing the search
        db: Database session
        query: Search query (semantic or keyword)
        date_filter: Optional date filter ('today', 'yesterday', 'this_week', 'last_7_days', 'last_30_days', or YYYY-MM-DD)
        sender_filter: Optional sender email filter
        limit: Maximum results (1-50)
        
    Returns:
        Dict with matching emails
    """
    from app.models.email import Email
    from datetime import date, timedelta
    from sqlalchemy import and_, or_, func
    
    try:
        # Validate limit
        if limit < 1 or limit > 50:
            limit = 10
        
        # Build query
        conditions = [Email.user_id == user.id]
        
        # Date filtering
        if date_filter:
            today = date.today()
            
            if date_filter == "today":
                conditions.append(func.date(Email.received_at) == today)
            elif date_filter == "yesterday":
                conditions.append(func.date(Email.received_at) == today - timedelta(days=1))
            elif date_filter == "this_week":
                week_start = today - timedelta(days=today.weekday())
                conditions.append(Email.received_at >= week_start)
            elif date_filter == "last_7_days":
                conditions.append(Email.received_at >= today - timedelta(days=7))
            elif date_filter == "last_30_days":
                conditions.append(Email.received_at >= today - timedelta(days=30))
            else:
                # Try parsing as specific date (YYYY-MM-DD)
                try:
                    from datetime import datetime
                    specific_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
                    conditions.append(func.date(Email.received_at) == specific_date)
                except ValueError:
                    logger.warning(f"Invalid date_filter format: {date_filter}")
        
        # Sender filtering
        if sender_filter:
            conditions.append(Email.sender.ilike(f"%{sender_filter}%"))
        
        # Text search (search in subject and body)
        if query:
            search_pattern = f"%{query}%"
            conditions.append(
                or_(
                    Email.subject.ilike(search_pattern),
                    Email.body_plain.ilike(search_pattern),
                )
            )
        
        # Execute query
        emails = db.query(Email).filter(and_(*conditions)).order_by(
            Email.received_at.desc()
        ).limit(limit).all()
        
        # Format results
        results = []
        for email in emails:
            # Get snippet from body
            snippet = ""
            if email.body_plain:
                snippet = email.body_plain[:200] + ("..." if len(email.body_plain) > 200 else "")
            
            results.append({
                "email_id": email.gmail_id,
                "subject": email.subject,
                "sender": email.sender,
                "received_at": email.received_at.isoformat() if email.received_at else None,
                "snippet": snippet,
                "labels": email.labels,
            })
        
        return {
            "status": "success",
            "total": len(results),
            "query": query,
            "date_filter": date_filter,
            "sender_filter": sender_filter,
            "emails": results,
        }
        
    except Exception as e:
        raise ToolExecutionError(f"Failed to search emails: {str(e)}")


async def search_calendar(
    user: User,
    db: Session,
    query: str,
    date_filter: Optional[str] = None,
    attendee_filter: Optional[str] = None,
    limit: int = 10,
) -> dict[str, Any]:
    """
    Search through calendar events using vector store.
    
    Args:
        user: User performing the search
        db: Database session
        query: Search query for event title/description
        date_filter: Optional date filter ('today', 'tomorrow', 'this_week', 'next_week', 'this_month', or YYYY-MM-DD)
        attendee_filter: Optional attendee email filter
        limit: Maximum results (1-50)
        
    Returns:
        Dict with matching calendar events
    """
    from app.models.vector_item import VectorItem
    from datetime import date, timedelta, datetime
    from sqlalchemy import and_, or_, func
    
    try:
        # Validate limit
        if limit < 1 or limit > 50:
            limit = 10
        
        # Build query on vector_item
        conditions = [
            VectorItem.user_id == user.id,
            VectorItem.source_type == "calendar",
        ]
        
        # Text search
        if query:
            search_pattern = f"%{query}%"
            conditions.append(VectorItem.text.ilike(search_pattern))
        
        # Execute query
        vector_items = db.query(VectorItem).filter(and_(*conditions)).order_by(
            VectorItem.created_at.desc()
        ).limit(limit * 2).all()  # Get extra to filter by date/attendee
        
        # Parse and filter results
        results = []
        today = date.today()
        
        for item in vector_items:
            # Parse metadata
            metadata = item.metadata_json or {}
            
            # Date filtering on metadata if available
            event_start = metadata.get("start_time")
            if date_filter and event_start:
                try:
                    event_date = datetime.fromisoformat(event_start.replace("Z", "+00:00")).date()
                    
                    if date_filter == "today" and event_date != today:
                        continue
                    elif date_filter == "tomorrow" and event_date != today + timedelta(days=1):
                        continue
                    elif date_filter == "this_week":
                        week_start = today - timedelta(days=today.weekday())
                        week_end = week_start + timedelta(days=6)
                        if not (week_start <= event_date <= week_end):
                            continue
                    elif date_filter == "next_week":
                        next_week_start = today + timedelta(days=(7 - today.weekday()))
                        next_week_end = next_week_start + timedelta(days=6)
                        if not (next_week_start <= event_date <= next_week_end):
                            continue
                    elif date_filter == "this_month":
                        if event_date.month != today.month or event_date.year != today.year:
                            continue
                    else:
                        # Try specific date
                        try:
                            specific_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
                            if event_date != specific_date:
                                continue
                        except ValueError:
                            pass
                except Exception as e:
                    logger.warning(f"Error parsing event date: {e}")
            
            # Attendee filtering
            if attendee_filter:
                attendees = metadata.get("attendees", [])
                if not any(attendee_filter.lower() in att.lower() for att in attendees):
                    continue
            
            results.append({
                "event_id": item.source_id,
                "summary": metadata.get("summary", "Untitled Event"),
                "start_time": metadata.get("start_time"),
                "end_time": metadata.get("end_time"),
                "location": metadata.get("location"),
                "attendees": metadata.get("attendees", []),
                "description": metadata.get("description", ""),
            })
            
            if len(results) >= limit:
                break
        
        return {
            "status": "success",
            "total": len(results),
            "query": query,
            "date_filter": date_filter,
            "attendee_filter": attendee_filter,
            "events": results,
        }
        
    except Exception as e:
        raise ToolExecutionError(f"Failed to search calendar: {str(e)}")


# Tool execution dispatcher
async def execute_tool(
    tool_name: str,
    arguments: dict[str, Any],
    user: User,
    db: Session,
) -> dict[str, Any]:
    """
    Execute a tool by name with given arguments.
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments
        user: User executing the tool
        db: Database session
        
    Returns:
        Tool execution result
        
    Raises:
        ToolExecutionError: If execution fails
    """
    if tool_name == "send_email":
        return await send_email(
            user=user,
            to=arguments.get("to", []),
            subject=arguments.get("subject", ""),
            body=arguments.get("body", ""),
            cc=arguments.get("cc"),
            bcc=arguments.get("bcc"),
        )
    
    elif tool_name == "schedule_event":
        return await schedule_event(
            user=user,
            db=db,
            summary=arguments.get("summary", ""),
            start_time=arguments.get("start_time", ""),
            end_time=arguments.get("end_time", ""),
            description=arguments.get("description"),
            attendees=arguments.get("attendees"),
            location=arguments.get("location"),
        )
    
    elif tool_name == "update_event":
        return await update_event(
            user=user,
            db=db,
            event_id=arguments.get("event_id", ""),
            summary=arguments.get("summary"),
            start_time=arguments.get("start_time"),
            end_time=arguments.get("end_time"),
            description=arguments.get("description"),
            attendees=arguments.get("attendees"),
            location=arguments.get("location"),
        )
    
    elif tool_name == "cancel_event":
        return await cancel_event(
            user=user,
            db=db,
            event_id=arguments.get("event_id", ""),
            send_updates=arguments.get("send_updates", True),
        )
    
    elif tool_name == "find_contact":
        return await find_contact(
            user=user,
            query=arguments.get("query", ""),
            limit=arguments.get("limit", 5),
        )
    
    elif tool_name == "create_contact":
        return await create_contact(
            user=user,
            email=arguments.get("email", ""),
            first_name=arguments.get("first_name"),
            last_name=arguments.get("last_name"),
            phone=arguments.get("phone"),
            company=arguments.get("company"),
            notes=arguments.get("notes"),
            job_title=arguments.get("job_title"),
            website=arguments.get("website"),
            city=arguments.get("city"),
            state=arguments.get("state"),
            zip_code=arguments.get("zip_code"),
            country=arguments.get("country"),
            lifecycle_stage=arguments.get("lifecycle_stage"),
        )
    
    elif tool_name == "update_contact":
        return await update_contact(
            user=user,
            contact_id=arguments.get("contact_id", ""),
            email=arguments.get("email"),
            first_name=arguments.get("first_name"),
            last_name=arguments.get("last_name"),
            phone=arguments.get("phone"),
            company=arguments.get("company"),
            job_title=arguments.get("job_title"),
            website=arguments.get("website"),
            city=arguments.get("city"),
            state=arguments.get("state"),
            zip_code=arguments.get("zip_code"),
            country=arguments.get("country"),
            lifecycle_stage=arguments.get("lifecycle_stage"),
        )
    
    elif tool_name == "create_note":
        return await create_note(
            user=user,
            contact_id=arguments.get("contact_id", ""),
            note_body=arguments.get("note_body", ""),
        )
    
    elif tool_name == "create_memory_rule":
        return await create_memory_rule(
            user=user,
            db=db,
            rule_description=arguments.get("rule_description", ""),
        )
    
    elif tool_name == "list_memory_rules":
        return await list_memory_rules(
            user=user,
            db=db,
        )
    
    elif tool_name == "search_emails":
        return await search_emails(
            user=user,
            db=db,
            query=arguments.get("query", ""),
            date_filter=arguments.get("date_filter"),
            sender_filter=arguments.get("sender_filter"),
            limit=arguments.get("limit", 10),
        )
    
    elif tool_name == "search_calendar":
        return await search_calendar(
            user=user,
            db=db,
            query=arguments.get("query", ""),
            date_filter=arguments.get("date_filter"),
            attendee_filter=arguments.get("attendee_filter"),
            limit=arguments.get("limit", 10),
        )
    
    else:
        raise ToolExecutionError(f"Unknown tool: {tool_name}")
