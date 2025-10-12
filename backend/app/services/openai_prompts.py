"""
OpenAI prompts and function schemas for the Financial Advisor AI agent.

This module contains:
- System prompt templates for the AI agent
- Function calling schemas for tools (send_email, schedule_event, find_contact, create_contact)
- Helper functions to build prompts with retrieved context
"""

from typing import Any
from datetime import datetime, timezone


def get_base_system_prompt() -> str:
    """Get base system prompt with current date."""
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    
    return f"""Financial advisor AI | Date: {date_str}

DATA AVAILABLE:
- Emails: Last 100 emails synced (search via context)
- Calendar: Events from last 60 days + next 90 days (if available in context, use them!)
- Contacts: Search via find_contact tool

ACTIONS AVAILABLE:
- send_email: Send emails via Gmail
- schedule_event: Create new calendar events
- update_event: Update existing events (requires Event ID from context)
- cancel_event: Cancel/delete events (requires Event ID from context)
- find_contact: Search HubSpot contacts
- create_contact: Add new contacts to HubSpot

RESPONSE FORMAT:
When listing calendar events, use this clean format with line breaks:

Example for MULTIPLE events:
Aqui estão seus próximos eventos:

📅 Meeting A - Oct 13, 09:00-10:00 (confirmed)

📅 Meeting B - Oct 13, 11:00-12:00 (confirmed)

📅 Meeting C - Oct 13, 14:00-15:00 (confirmed)

When listing emails, use this format:
Aqui estão seus últimos emails:

📧 From: sender@example.com
   Subject: Meeting recap
   Date: Oct 12, 2025

📧 From: another@example.com
   Subject: Follow-up
   Date: Oct 11, 2025

When confirming actions with MULTIPLE items:
✅ 5 eventos criados:

📅 Evento A - Oct 13, 09:00-10:00 (confirmed)

📅 Evento B - Oct 13, 10:00-11:00 (confirmed)

📅 Evento C - Oct 13, 11:00-12:00 (confirmed)

CRITICAL: Add DOUBLE line breaks (\\n\\n) between each item (events, emails, contacts) for readability.

IMPORTANT: 
- Check the retrieved context first. If calendar events are present, use them to answer.
- ALSO CHECK the conversation history - if you just created/cancelled an event in the previous message, it exists even if not in the retrieved context yet.
- Calendar events in context include an Event ID field - use this ID for update_event or cancel_event.
- If no events found in BOTH context AND conversation history, say "No upcoming events found".
- When user refers to "this event" or "that event", look at the conversation history to identify which event they mean.
- Use event names/titles from the conversation history to find the corresponding Event ID in the retrieved context.
- After executing a tool, confirm the action briefly in the same language as the user's message.
- Keep responses conversational and natural, avoiding robotic or technical language.
- When user asks to cancel/update/create MULTIPLE items, make MULTIPLE tool calls (one for each item).
- FORMATTING: Always use line breaks (\n) between list items - NEVER put multiple events/items in a single line or paragraph.
- MEMORY: Remember events you just created/cancelled/updated in THIS conversation - they are real even if not yet in the retrieved context."""


# Function schemas for OpenAI function calling
FUNCTION_SCHEMAS = [
    {
        "name": "send_email",
        "description": "Send an email via Gmail. Use this when the user asks to send an email, reply to someone, or follow up with a contact.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of recipient email addresses (required)",
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line (required)",
                },
                "body": {
                    "type": "string",
                    "description": "Email body content in plain text or HTML (required)",
                },
                "cc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of CC email addresses (optional)",
                },
                "bcc": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of BCC email addresses (optional)",
                },
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "schedule_event",
        "description": "Schedule a calendar event in Google Calendar. Use this when the user asks to schedule a meeting, create an event, or book time.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Event title/summary (required)",
                },
                "start_time": {
                    "type": "string",
                    "description": "Event start time in ISO 8601 format (e.g., '2025-10-15T10:00:00-06:00') (required)",
                },
                "end_time": {
                    "type": "string",
                    "description": "Event end time in ISO 8601 format (e.g., '2025-10-15T11:00:00-06:00') (required)",
                },
                "description": {
                    "type": "string",
                    "description": "Event description/notes (optional)",
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of attendee email addresses (optional)",
                },
                "location": {
                    "type": "string",
                    "description": "Event location (optional)",
                },
            },
            "required": ["summary", "start_time", "end_time"],
        },
    },
    {
        "name": "update_event",
        "description": "Update an existing calendar event in Google Calendar. Use this when the user asks to change, reschedule, or modify an event. You can update time, title, description, location, or attendees.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "Google Calendar event ID (found in event metadata from search results) (required)",
                },
                "summary": {
                    "type": "string",
                    "description": "New event title/summary (optional)",
                },
                "start_time": {
                    "type": "string",
                    "description": "New start time in ISO 8601 format (e.g., '2025-10-15T10:00:00-06:00') (optional)",
                },
                "end_time": {
                    "type": "string",
                    "description": "New end time in ISO 8601 format (e.g., '2025-10-15T11:00:00-06:00') (optional)",
                },
                "description": {
                    "type": "string",
                    "description": "New event description/notes (optional)",
                },
                "attendees": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "New list of attendee email addresses (optional)",
                },
                "location": {
                    "type": "string",
                    "description": "New event location (optional)",
                },
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "cancel_event",
        "description": "Cancel (delete) a calendar event in Google Calendar. Use this when the user asks to cancel, delete, or remove an event.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "Google Calendar event ID (found in event metadata from search results) (required)",
                },
                "send_updates": {
                    "type": "boolean",
                    "description": "Whether to send cancellation notifications to attendees (default: true)",
                    "default": True,
                },
            },
            "required": ["event_id"],
        },
    },
    {
        "name": "find_contact",
        "description": "Search for a contact in HubSpot CRM by name, email, or company. Use this when the user asks about a specific person or company.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (name, email, or company) (required)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5, min: 1, max: 100)",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 100,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "create_contact",
        "description": "Create a new contact in HubSpot CRM. Use this when the user asks to add a new contact or save someone's information.",
        "parameters": {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "Contact's email address (required)",
                },
                "first_name": {
                    "type": "string",
                    "description": "Contact's first name (optional)",
                },
                "last_name": {
                    "type": "string",
                    "description": "Contact's last name (optional)",
                },
                "phone": {
                    "type": "string",
                    "description": "Contact's phone number (optional)",
                },
                "company": {
                    "type": "string",
                    "description": "Contact's company name (optional)",
                },
                "job_title": {
                    "type": "string",
                    "description": "Contact's job title (optional)",
                },
                "website": {
                    "type": "string",
                    "description": "Contact's website URL (optional)",
                },
                "city": {
                    "type": "string",
                    "description": "Contact's city (optional)",
                },
                "state": {
                    "type": "string",
                    "description": "Contact's state or region (optional)",
                },
                "zip_code": {
                    "type": "string",
                    "description": "Contact's postal/zip code (optional)",
                },
                "country": {
                    "type": "string",
                    "description": "Contact's country (optional)",
                },
                "lifecycle_stage": {
                    "type": "string",
                    "description": "Contact's lifecycle stage: subscriber, lead, marketingqualifiedlead, salesqualifiedlead, opportunity, customer, evangelist, other (optional)",
                },
                "notes": {
                    "type": "string",
                    "description": "Initial notes about the contact. Will be created as a separate note engagement (optional)",
                },
            },
            "required": ["email"],
        },
    },
    {
        "name": "update_contact",
        "description": "Update an existing contact in HubSpot CRM. Use this to modify contact information, change lifecycle stage, or update any contact field.",
        "parameters": {
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "string",
                    "description": "HubSpot contact ID to update (from find_contact)",
                },
                "email": {
                    "type": "string",
                    "description": "Updated email address (optional)",
                },
                "first_name": {
                    "type": "string",
                    "description": "Updated first name (optional)",
                },
                "last_name": {
                    "type": "string",
                    "description": "Updated last name (optional)",
                },
                "phone": {
                    "type": "string",
                    "description": "Updated phone number (optional)",
                },
                "company": {
                    "type": "string",
                    "description": "Updated company name (optional)",
                },
                "job_title": {
                    "type": "string",
                    "description": "Updated job title (optional)",
                },
                "website": {
                    "type": "string",
                    "description": "Updated website URL (optional)",
                },
                "city": {
                    "type": "string",
                    "description": "Updated city (optional)",
                },
                "state": {
                    "type": "string",
                    "description": "Updated state or region (optional)",
                },
                "zip_code": {
                    "type": "string",
                    "description": "Updated postal/zip code (optional)",
                },
                "country": {
                    "type": "string",
                    "description": "Updated country (optional)",
                },
                "lifecycle_stage": {
                    "type": "string",
                    "description": "Updated lifecycle stage: subscriber, lead, marketingqualifiedlead, salesqualifiedlead, opportunity, customer, evangelist, other (optional)",
                },
            },
            "required": ["contact_id"],
        },
    },
    {
        "name": "create_note",
        "description": "Create a note in HubSpot and associate it with a contact. Use this to log interactions, add details, or record important information about a contact.",
        "parameters": {
            "type": "object",
            "properties": {
                "contact_id": {
                    "type": "string",
                    "description": "HubSpot contact ID (from find_contact or create_contact)",
                },
                "note_body": {
                    "type": "string",
                    "description": "Text content of the note. Can include details about interactions, meetings, or any important information.",
                },
            },
            "required": ["contact_id", "note_body"],
        },
    },
    {
        "name": "create_memory_rule",
        "description": "Create a persistent memory rule that the AI will remember and apply automatically. Use this when the user gives ongoing instructions like 'When someone emails me that is not in Hubspot, create a contact' or 'When I create a contact, send them a welcome email'. These rules persist across sessions and are triggered by webhooks/events.",
        "parameters": {
            "type": "object",
            "properties": {
                "rule_description": {
                    "type": "string",
                    "description": "Natural language description of what the rule should do (required). Example: 'When someone emails me that is not in Hubspot, create a contact in Hubspot with a note about the email.'",
                },
            },
            "required": ["rule_description"],
        },
    },
]


def build_system_prompt_with_context(
    retrieved_context: list[dict[str, Any]],
    max_context_tokens: int = 4000,
) -> str:
    """
    Build system prompt with retrieved context from RAG.
    
    Args:
        retrieved_context: List of retrieved chunks with metadata
        max_context_tokens: Maximum tokens to include in context
        
    Returns:
        System prompt with context included
    """
    base_prompt = get_base_system_prompt()
    
    if not retrieved_context:
        return base_prompt
    
    # Build context section
    context_parts = ["\n\n**Retrieved Context:**\n"]
    
    for idx, item in enumerate(retrieved_context, 1):
        source_type = item.get("source_type", "unknown")
        text = item.get("text", "")
        similarity = item.get("similarity", 0.0)
        
        # Extract email metadata if available
        email_info = item.get("email", {})
        calendar_metadata = item.get("metadata", {})
        
        if source_type == "email" and email_info:
            subject = email_info.get("subject", "N/A")
            sender = email_info.get("sender", "N/A")
            received_at = email_info.get("received_at", "N/A")
            
            # Limit text length to save tokens
            text_preview = text[:800] + "..." if len(text) > 800 else text
            
            # Format email with limited content
            email_text = f"""[Email {idx}]
Subject: {subject}
From: {sender}
Date: {received_at}

Content:
{text_preview}
---"""
            context_parts.append(f"\n{email_text}\n")
        elif source_type == "calendar" and calendar_metadata:
            # Format calendar event with event_id for updates/cancellation
            event_id = calendar_metadata.get("event_id", "N/A")
            summary = calendar_metadata.get("summary", "N/A")
            start = calendar_metadata.get("start", "N/A")
            end = calendar_metadata.get("end", "N/A")
            
            # Limit text length to save tokens
            text_preview = text[:600] + "..." if len(text) > 600 else text
            
            calendar_text = f"""[Calendar Event {idx}]
Event ID: {event_id}
Title: {summary}
Start: {start}
End: {end}

{text_preview}
---"""
            context_parts.append(f"\n{calendar_text}\n")
        else:
            # For other sources
            metadata_str = f"[Source {idx}: {source_type}]"
            context_parts.append(f"\n{metadata_str}\n{text[:400]}...\n")
    
    context_text = "".join(context_parts)
    
    return base_prompt + context_text


def validate_function_call(function_name: str, arguments: dict[str, Any]) -> tuple[bool, str]:
    """
    Validate function call parameters before execution.
    
    Args:
        function_name: Name of the function to call
        arguments: Arguments provided by the model
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if function_name == "send_email":
        return _validate_send_email(arguments)
    elif function_name == "schedule_event":
        return _validate_schedule_event(arguments)
    elif function_name == "update_event":
        return _validate_update_event(arguments)
    elif function_name == "cancel_event":
        return _validate_cancel_event(arguments)
    elif function_name == "find_contact":
        return _validate_find_contact(arguments)
    elif function_name == "create_contact":
        return _validate_create_contact(arguments)
    elif function_name == "update_contact":
        return _validate_update_contact(arguments)
    elif function_name == "create_note":
        return _validate_create_note(arguments)
    elif function_name == "create_memory_rule":
        return _validate_create_memory_rule(arguments)
    else:
        return False, f"Unknown function: {function_name}"


def _validate_send_email(args: dict[str, Any]) -> tuple[bool, str]:
    """Validate send_email arguments."""
    import re
    
    # Check required fields
    if "to" not in args or not args["to"]:
        return False, "Missing required field: 'to'"
    if "subject" not in args or not args["subject"]:
        return False, "Missing required field: 'subject'"
    if "body" not in args or not args["body"]:
        return False, "Missing required field: 'body'"
    
    # Validate email addresses (RFC 5322 simplified)
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    
    for email in args["to"]:
        if not email_pattern.match(email):
            return False, f"Invalid email address: {email}"
    
    # Validate CC if provided
    if "cc" in args and args["cc"]:
        for email in args["cc"]:
            if not email_pattern.match(email):
                return False, f"Invalid CC email address: {email}"
    
    # Validate BCC if provided
    if "bcc" in args and args["bcc"]:
        for email in args["bcc"]:
            if not email_pattern.match(email):
                return False, f"Invalid BCC email address: {email}"
    
    return True, ""


def _validate_schedule_event(args: dict[str, Any]) -> tuple[bool, str]:
    """Validate schedule_event arguments."""
    from datetime import datetime
    
    # Check required fields
    if "summary" not in args or not args["summary"]:
        return False, "Missing required field: 'summary'"
    if "start_time" not in args or not args["start_time"]:
        return False, "Missing required field: 'start_time'"
    if "end_time" not in args or not args["end_time"]:
        return False, "Missing required field: 'end_time'"
    
    # Validate datetime format (ISO 8601)
    try:
        start = datetime.fromisoformat(args["start_time"])
        end = datetime.fromisoformat(args["end_time"])
        
        # Check that end is after start
        if end <= start:
            return False, "Event end time must be after start time"
        
    except ValueError as e:
        return False, f"Invalid datetime format: {str(e)}"
    
    # Validate attendee emails if provided
    if "attendees" in args and args["attendees"]:
        import re
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        for email in args["attendees"]:
            if not email_pattern.match(email):
                return False, f"Invalid attendee email address: {email}"
    
    return True, ""


def _validate_update_event(args: dict[str, Any]) -> tuple[bool, str]:
    """Validate update_event arguments."""
    from datetime import datetime
    import re
    
    # Check required field
    if "event_id" not in args or not args["event_id"]:
        return False, "Missing required field: 'event_id'"
    
    # Validate datetime format if provided
    if "start_time" in args and args["start_time"]:
        try:
            datetime.fromisoformat(args["start_time"])
        except ValueError as e:
            return False, f"Invalid start_time format: {str(e)}"
    
    if "end_time" in args and args["end_time"]:
        try:
            datetime.fromisoformat(args["end_time"])
        except ValueError as e:
            return False, f"Invalid end_time format: {str(e)}"
    
    # Check that end is after start if both provided
    if "start_time" in args and "end_time" in args:
        try:
            start = datetime.fromisoformat(args["start_time"])
            end = datetime.fromisoformat(args["end_time"])
            if end <= start:
                return False, "Event end time must be after start time"
        except ValueError:
            pass  # Already validated above
    
    # Validate attendee emails if provided
    if "attendees" in args and args["attendees"]:
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        for email in args["attendees"]:
            if not email_pattern.match(email):
                return False, f"Invalid attendee email address: {email}"
    
    return True, ""


def _validate_cancel_event(args: dict[str, Any]) -> tuple[bool, str]:
    """Validate cancel_event arguments."""
    # Check required field
    if "event_id" not in args or not args["event_id"]:
        return False, "Missing required field: 'event_id'"
    
    # Validate send_updates if provided
    if "send_updates" in args and not isinstance(args["send_updates"], bool):
        return False, "send_updates must be a boolean"
    
    return True, ""


def _validate_find_contact(args: dict[str, Any]) -> tuple[bool, str]:
    """Validate find_contact arguments."""
    if "query" not in args or not args["query"]:
        return False, "Missing required field: 'query'"
    
    # Validate limit if provided
    if "limit" in args:
        try:
            limit = int(args["limit"])
            if limit < 1 or limit > 100:
                return False, "Limit must be between 1 and 100"
        except (ValueError, TypeError):
            return False, "Invalid limit value"
    
    return True, ""


def _validate_create_contact(args: dict[str, Any]) -> tuple[bool, str]:
    """Validate create_contact arguments."""
    import re
    
    # Check required field
    if "email" not in args or not args["email"]:
        return False, "Missing required field: 'email'"
    
    # Validate email address
    email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    if not email_pattern.match(args["email"]):
        return False, f"Invalid email address: {args['email']}"
    
    return True, ""


def _validate_update_contact(args: dict[str, Any]) -> tuple[bool, str]:
    """Validate update_contact arguments."""
    import re
    
    # Check required field
    if "contact_id" not in args or not args["contact_id"]:
        return False, "Missing required field: 'contact_id'"
    
    # Validate email if provided
    if "email" in args and args["email"]:
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        if not email_pattern.match(args["email"]):
            return False, f"Invalid email address: {args['email']}"
    
    return True, ""


def _validate_create_note(args: dict[str, Any]) -> tuple[bool, str]:
    """Validate create_note arguments."""
    # Check required fields
    if "contact_id" not in args or not args["contact_id"]:
        return False, "Missing required field: 'contact_id'"
    
    if "note_body" not in args or not args["note_body"]:
        return False, "Missing required field: 'note_body'"
    
    return True, ""


def _validate_create_memory_rule(args: dict[str, Any]) -> tuple[bool, str]:
    """Validate create_memory_rule arguments."""
    # Check required field
    if "rule_description" not in args or not args["rule_description"]:
        return False, "Missing required field: 'rule_description'"
    
    # Validate minimum length
    if len(args["rule_description"].strip()) < 10:
        return False, "Rule description must be at least 10 characters"
    
    return True, ""
