"""
OpenAI prompts and function schemas for the Financial Advisor AI agent.

This module contains:
- System prompt templates for the AI agent
- Function calling schemas for tools (send_email, schedule_event, find_contact, create_contact)
- Helper functions to build prompts with retrieved context
"""

from typing import Any


# System prompt for the Financial Advisor AI agent
FINANCIAL_ADVISOR_SYSTEM_PROMPT = """You are an intelligent AI assistant for a financial advisor.

Your role is to help the financial advisor by:
1. **Answering questions** about emails, contacts, and notes using the context provided
2. **Finding information** from the advisor's CRM (HubSpot) and email (Gmail)
3. **Taking actions** when requested, such as:
   - Sending emails
   - Scheduling calendar events
   - Creating or finding contacts in HubSpot
   - Creating tasks for follow-up

**Important guidelines:**
- Always cite sources when answering from retrieved context (use the source IDs provided)
- If you don't have enough information, say so clearly
- For actions (sending emails, scheduling events), confirm details before executing
- Treat all information as confidential and professional
- Use the provided context to give accurate, specific answers
- If the context doesn't contain relevant information, acknowledge this limitation

**Context format:**
Retrieved documents will be provided as quoted text with source IDs. These are from the advisor's emails and CRM.
Use this information to answer questions accurately.

**Available tools:**
You have access to tools for sending emails, scheduling events, and managing contacts.
Use these tools when explicitly requested by the user.
"""


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
                    "description": "Maximum number of results to return (default: 5)",
                    "default": 5,
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
                "notes": {
                    "type": "string",
                    "description": "Additional notes about the contact (optional)",
                },
            },
            "required": ["email"],
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
    if not retrieved_context:
        return FINANCIAL_ADVISOR_SYSTEM_PROMPT
    
    # Build context section
    context_parts = ["\n\n**Retrieved Context:**\n"]
    
    for idx, item in enumerate(retrieved_context, 1):
        source_type = item.get("source_type", "unknown")
        text = item.get("text", "")
        similarity = item.get("similarity", 0.0)
        
        # Include metadata for citation
        metadata_str = f"[Source {idx}: {source_type}, relevance: {similarity:.2f}]"
        
        context_parts.append(f"\n{metadata_str}\n```\n{text}\n```\n")
    
    context_text = "".join(context_parts)
    
    # Note: In production, implement proper token counting here
    # For now, we'll trust that RAGService.get_context_for_query() 
    # already handled token budgeting
    
    return FINANCIAL_ADVISOR_SYSTEM_PROMPT + context_text


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
    elif function_name == "find_contact":
        return _validate_find_contact(arguments)
    elif function_name == "create_contact":
        return _validate_create_contact(arguments)
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
