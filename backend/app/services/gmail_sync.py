"""Gmail synchronization service for ingesting emails into the database."""
import base64
import logging
import time
from datetime import datetime
from typing import Any, Optional

from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models.email import Email
from ..models.user import User
from .memory_rules import evaluate_rules_for_event


logger = logging.getLogger(__name__)


class GmailSyncService:
    """Service for syncing Gmail messages to the database."""

    def __init__(self, user: User, db: Session):
        """Initialize Gmail sync service.
        
        Args:
            user: User with valid Google OAuth tokens
            db: Database session for storing emails
        """
        self.user = user
        self.db = db
        self.credentials = self._build_credentials()
        self.service = build("gmail", "v1", credentials=self.credentials)
    
    def _build_credentials(self) -> Credentials:
        """Build Google credentials from user's OAuth tokens.
        
        Returns:
            Credentials object for Gmail API
            
        Raises:
            ValueError: If user doesn't have valid Google OAuth tokens
        """
        if not self.user.google_oauth_tokens:
            raise ValueError(f"User {self.user.id} has no Google OAuth tokens")
        
        tokens = self.user.google_oauth_tokens
        
        credentials = Credentials(
            token=tokens.get("access_token"),
            refresh_token=tokens.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=tokens.get("client_id"),
            client_secret=tokens.get("client_secret"),
            scopes=tokens.get("scopes", [])
        )
        
        return credentials
    
    def sync(
        self,
        max_results: int = 100,
        query: str = "in:inbox OR in:sent",
        **kwargs: Any
    ) -> dict[str, Any]:
        """Sync Gmail messages to database.
        
        Args:
            max_results: Maximum number of messages to fetch
            query: Gmail search query (default: inbox and sent)
            **kwargs: Additional parameters for Gmail API
            
        Returns:
            Dict with sync statistics:
                - total_fetched: Number of messages fetched
                - new_emails: Number of new emails created
                - updated_emails: Number of existing emails updated
                - errors: List of error messages
        """
        stats = {
            "total_fetched": 0,
            "new_emails": 0,
            "updated_emails": 0,
            "errors": []
        }
        
        try:
            # List messages with pagination
            messages = self._list_messages(query=query, max_results=max_results)
            stats["total_fetched"] = len(messages)
            
            # Fetch and process each message
            for message_id in messages:
                try:
                    self._process_message(message_id, stats)
                except Exception as e:
                    error_msg = f"Error processing message {message_id}: {str(e)}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)
            
            # Commit all changes
            self.db.commit()
            
            logger.info(
                f"Gmail sync complete for user {self.user.id}: "
                f"{stats['new_emails']} new, {stats['updated_emails']} updated"
            )
            
        except Exception as e:
            error_msg = f"Gmail sync failed for user {self.user.id}: {str(e)}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
            self.db.rollback()
        
        return stats
    
    def _list_messages(
        self,
        query: str = "",
        max_results: int = 100
    ) -> list[str]:
        """List message IDs matching the query.
        
        Args:
            query: Gmail search query
            max_results: Maximum number of message IDs to return
            
        Returns:
            List of Gmail message IDs
        """
        message_ids: list[str] = []
        page_token: Optional[str] = None
        
        while len(message_ids) < max_results:
            try:
                # Call Gmail API with exponential backoff
                results = self._api_call_with_retry(
                    lambda: self.service.users().messages().list(
                        userId="me",
                        q=query,
                        maxResults=min(500, max_results - len(message_ids)),
                        pageToken=page_token
                    ).execute()
                )
                
                messages = results.get("messages", [])
                message_ids.extend([msg["id"] for msg in messages])
                
                # Check if there are more pages
                page_token = results.get("nextPageToken")
                if not page_token:
                    break
                    
            except HttpError as e:
                logger.error(f"Error listing messages: {e}")
                break
        
        return message_ids[:max_results]
    
    def _process_message(self, message_id: str, stats: dict[str, Any]) -> None:
        """Fetch and process a single Gmail message.
        
        Args:
            message_id: Gmail message ID
            stats: Stats dict to update
        """
        # Check if email already exists (idempotency)
        existing_email = self.db.scalars(
            select(Email).where(Email.gmail_id == message_id)
        ).first()
        
        # Fetch message details
        message_data = self._api_call_with_retry(
            lambda: self.service.users().messages().get(
                userId="me",
                id=message_id,
                format="full"
            ).execute()
        )
        
        # Parse message
        email_data = self._parse_message(message_data)
        
        if existing_email:
            # Update existing email
            for key, value in email_data.items():
                setattr(existing_email, key, value)
            stats["updated_emails"] += 1
            logger.debug(f"Updated email {message_id}")
        else:
            # Create new email
            if not self.user.id:
                raise ValueError("User ID is required")
            
            new_email = Email(
                user_id=self.user.id,
                gmail_id=message_id,
                **email_data
            )
            self.db.add(new_email)
            self.db.flush()  # Ensure the email has an ID
            stats["new_emails"] += 1
            logger.debug(f"Created new email {message_id}")
            
            # Trigger memory rules for new email
            try:
                import asyncio
                received_at_str = None
                if email_data.get("received_at"):
                    received_at_str = email_data["received_at"].isoformat()
                
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, create a task
                    asyncio.create_task(evaluate_rules_for_event(
                        db=self.db,
                        user=self.user,
                        event_type="gmail.email_received",
                        event_data={
                            "email_id": new_email.id,
                            "gmail_id": message_id,
                            "subject": email_data.get("subject"),
                            "sender": email_data.get("sender_email"),
                            "sender_name": email_data.get("sender_name"),
                            "received_at": received_at_str,
                            "snippet": email_data.get("snippet"),
                            "labels": email_data.get("labels", [])
                        }
                    ))
                else:
                    # If no loop, run synchronously
                    loop.run_until_complete(evaluate_rules_for_event(
                        db=self.db,
                        user=self.user,
                        event_type="gmail.email_received",
                        event_data={
                            "email_id": new_email.id,
                            "gmail_id": message_id,
                            "subject": email_data.get("subject"),
                            "sender": email_data.get("sender_email"),
                            "sender_name": email_data.get("sender_name"),
                            "received_at": received_at_str,
                            "snippet": email_data.get("snippet"),
                            "labels": email_data.get("labels", [])
                        }
                    ))
            except Exception as e:
                logger.error(f"Error evaluating rules for new email {message_id}: {e}")
    
    def _parse_message(self, message_data: dict[str, Any]) -> dict[str, Any]:
        """Parse Gmail message data into Email model fields.
        
        Args:
            message_data: Raw Gmail API message data
            
        Returns:
            Dict with parsed email fields
        """
        payload = message_data.get("payload", {})
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
        
        # Extract basic fields
        subject = headers.get("subject", "(No Subject)")
        from_address = headers.get("from", "")
        to_address = headers.get("to", "")
        cc_address = headers.get("cc", "")
        bcc_address = headers.get("bcc", "")
        reply_to = headers.get("reply-to", "")
        date_str = headers.get("date", "")
        
        # Parse date
        try:
            # Gmail date format: "Thu, 10 Oct 2024 10:30:00 +0000"
            email_date = datetime.strptime(
                date_str.split("(")[0].strip(),
                "%a, %d %b %Y %H:%M:%S %z"
            )
        except (ValueError, AttributeError):
            email_date = datetime.now()
            logger.warning(f"Could not parse date: {date_str}")
        
        # Extract body
        body = self._extract_body(payload)
        
        # Sanitize HTML to plain text
        body_text = self._html_to_text(body)
        
        # Parse email lists
        to_recipients = [addr.strip() for addr in to_address.split(",")] if to_address else []
        cc_recipients = [addr.strip() for addr in cc_address.split(",")] if cc_address else []
        bcc_recipients = [addr.strip() for addr in bcc_address.split(",")] if bcc_address else []
        
        return {
            "subject": subject,
            "sender": from_address,  # Fixed: was 'from_address', should be 'sender'
            "reply_to": reply_to,
            "to_recipients": to_recipients,
            "cc_recipients": cc_recipients,
            "bcc_recipients": bcc_recipients,
            "body_plain": body_text,
            "body_html": body if "<" in body else None,
            "snippet": message_data.get("snippet", ""),
            "received_at": email_date,
            "sent_at": email_date,
            "headers_json": headers,
            "thread_id": message_data.get("threadId"),
            "labels": message_data.get("labelIds", []),
            "direction": "inbound" if "INBOX" in message_data.get("labelIds", []) else "outbound",
            "is_read": "UNREAD" not in message_data.get("labelIds", []),
        }
    
    def _extract_body(self, payload: dict[str, Any]) -> str:
        """Extract email body from Gmail payload.
        
        Args:
            payload: Gmail message payload
            
        Returns:
            Email body as string (HTML or plain text)
        """
        # Try to get body from parts
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                
                if part.get("mimeType") == "text/html":
                    data = part.get("body", {}).get("data", "")
                    if data:
                        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                
                # Recursive for nested parts
                if "parts" in part:
                    nested_body = self._extract_body(part)
                    if nested_body:
                        return nested_body
        
        # Try to get body directly
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")
        
        # Fallback to snippet
        return payload.get("snippet", "")
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text and sanitize.
        
        Args:
            html: HTML string
            
        Returns:
            Plain text string with scripts/styles removed
        """
        if not html:
            return ""
        
        try:
            # Parse HTML
            soup = BeautifulSoup(html, "html.parser")
            
            # Remove script and style tags
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text(separator="\n")
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            logger.error(f"Error converting HTML to text: {e}")
            # Return original if parsing fails
            return html
    
    def _api_call_with_retry(
        self,
        func: Any,
        max_retries: int = 5,
        initial_delay: float = 1.0
    ) -> Any:
        """Execute Gmail API call with exponential backoff retry.
        
        Args:
            func: Function to execute (should return API response)
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds (doubles each retry)
            
        Returns:
            API response
            
        Raises:
            HttpError: If all retries fail
        """
        delay = initial_delay
        
        for attempt in range(max_retries):
            try:
                return func()
            except HttpError as e:
                # Check if error is rate limit (429) or server error (5xx)
                if e.resp.status in [429, 500, 502, 503, 504]:
                    if attempt < max_retries - 1:
                        # Get retry-after header if available
                        retry_after = e.resp.get("retry-after")
                        if retry_after:
                            delay = float(retry_after)
                        
                        logger.warning(
                            f"Gmail API error {e.resp.status}, "
                            f"retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                        continue
                
                # Re-raise if not retryable or max retries reached
                raise
        
        # This should not be reached, but just in case
        raise HttpError(resp={"status": 429}, content=b"Max retries exceeded")
    
    def setup_push_notifications(self, topic_name: str) -> dict[str, Any]:
        """
        Set up Gmail push notifications via Pub/Sub.
        
        Calls Gmail API watch() to enable push notifications. Notifications expire
        after 7 days or when the history ID advances significantly.
        
        Args:
            topic_name: Full Pub/Sub topic name (projects/{project}/topics/{topic})
        
        Returns:
            Dict with watch response:
                - historyId: Starting history ID
                - expiration: Unix timestamp (milliseconds) when watch expires
        
        Raises:
            HttpError: If watch() call fails
        
        Documentation: https://developers.google.com/gmail/api/guides/push
        """
        try:
            watch_request = {
                "labelIds": ["INBOX"], 
                "topicName": topic_name
            }
            
            response = self.service.users().watch(
                userId="me",
                body=watch_request
            ).execute()
            
            logger.info(
                f"Gmail push notifications enabled for user {self.user.id}: "
                f"historyId={response.get('historyId')}, "
                f"expiration={response.get('expiration')}"
            )
            
            return response
            
        except HttpError as e:
            logger.error(f"Failed to setup Gmail push notifications: {e}")
            raise
    
    def stop_push_notifications(self) -> None:
        """
        Stop Gmail push notifications.
        
        Calls Gmail API stop() to disable push notifications.
        """
        try:
            self.service.users().stop(userId="me").execute()
            logger.info(f"Gmail push notifications stopped for user {self.user.id}")
        except HttpError as e:
            logger.error(f"Failed to stop Gmail push notifications: {e}")
            raise
