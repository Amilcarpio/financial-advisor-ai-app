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
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import httpx
from sqlmodel import Session, select

from app.models.user import User
from app.models.task import Task
from app.core.config import settings


# Rate limiting tracking (in-memory, should use Redis in production)
_email_rate_limits: dict[int, list[datetime]] = {}
MAX_EMAILS_PER_HOUR = 50
MAX_EMAILS_GLOBAL_PER_HOUR = 500


class ToolExecutionError(Exception):
    """Raised when a tool execution fails."""
    pass


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
        
        return {
            "status": "success",
            "event_id": result.get('id'),
            "event_link": result.get('htmlLink'),
            "summary": result.get('summary'),
            "start": result.get('start', {}).get('dateTime'),
            "end": result.get('end', {}).get('dateTime'),
            "attendees": attendees or [],
        }
        
    except HttpError as e:
        error_details = e.error_details if hasattr(e, 'error_details') else str(e)
        raise ToolExecutionError(f"Calendar API error: {error_details}")
    except Exception as e:
        raise ToolExecutionError(f"Failed to schedule event: {str(e)}")


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
        limit: Maximum number of results
        
    Returns:
        Dict with list of matching contacts
        
    Raises:
        ToolExecutionError: If search fails
    """
    if not user.hubspot_oauth_tokens:
        raise ToolExecutionError("HubSpot OAuth tokens not found. Please connect your HubSpot account.")
    
    try:
        # Get access token
        token_data = json.loads(user.hubspot_oauth_tokens) if isinstance(user.hubspot_oauth_tokens, str) else user.hubspot_oauth_tokens
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise ToolExecutionError("HubSpot access token not found")
        
        # Search contacts via HubSpot API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.hubapi.com/crm/v3/objects/contacts/search",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "filterGroups": [{
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
                    }],
                    "properties": ["firstname", "lastname", "email", "phone", "company"],
                    "limit": limit,
                },
                timeout=30.0,
            )
            
            response.raise_for_status()
            data = response.json()
            
            contacts = []
            for result in data.get("results", []):
                props = result.get("properties", {})
                contacts.append({
                    "id": result.get("id"),
                    "first_name": props.get("firstname"),
                    "last_name": props.get("lastname"),
                    "email": props.get("email"),
                    "phone": props.get("phone"),
                    "company": props.get("company"),
                })
            
            return {
                "status": "success",
                "total": len(contacts),
                "contacts": contacts,
            }
            
    except httpx.HTTPStatusError as e:
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
        notes: Additional notes
        
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
        if notes:
            properties["notes"] = notes
        
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
                # Contact already exists, try to find it
                search_result = await find_contact(user, email, limit=1)
                if search_result.get("contacts"):
                    existing = search_result["contacts"][0]
                    return {
                        "status": "exists",
                        "contact_id": existing["id"],
                        "message": "Contact with this email already exists",
                        "contact": existing,
                    }
            
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
            }
            
    except httpx.HTTPStatusError as e:
        raise ToolExecutionError(f"HubSpot API error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise ToolExecutionError(f"Failed to create contact: {str(e)}")


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
            summary=arguments.get("summary", ""),
            start_time=arguments.get("start_time", ""),
            end_time=arguments.get("end_time", ""),
            description=arguments.get("description"),
            attendees=arguments.get("attendees"),
            location=arguments.get("location"),
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
        )
    
    else:
        raise ToolExecutionError(f"Unknown tool: {tool_name}")
