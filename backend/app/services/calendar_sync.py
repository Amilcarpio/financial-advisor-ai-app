"""Google Calendar synchronization service for ingesting events into the database."""
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models.vector_item import VectorItem
from ..models.user import User
from .embeddings import EmbeddingService


logger = logging.getLogger(__name__)


class CalendarSyncService:
    """Service for syncing Google Calendar events to the database."""

    def __init__(self, user: User, db: Session):
        """Initialize Calendar sync service.
        
        Args:
            user: User with valid Google OAuth tokens
            db: Database session for storing events
        """
        self.user = user
        self.db = db
        self.credentials = self._build_credentials()
        self.service = build("calendar", "v3", credentials=self.credentials)
        self.embedding_service = EmbeddingService()
    
    def _build_credentials(self) -> Credentials:
        """Build Google credentials from user's OAuth tokens.
        
        Returns:
            Credentials object for Calendar API
            
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
        max_results: int = 250,
        calendar_id: str = "primary",
        **kwargs: Any
    ) -> dict[str, Any]:
        """Sync Google Calendar events to database.
        
        Args:
            max_results: Maximum number of events to fetch
            calendar_id: Calendar ID (default: 'primary')
            **kwargs: Additional parameters for Calendar API
            
        Returns:
            Dict with sync statistics:
                - total_fetched: Number of events fetched
                - new_events: Number of new events created
                - updated_events: Number of existing events updated
                - deleted_events: Number of events removed from vector store
                - errors: List of error messages
        """
        stats = {
            "total_fetched": 0,
            "new_events": 0,
            "updated_events": 0,
            "deleted_events": 0,
            "errors": []
        }
        
        try:
            # List events with pagination
            events = self._list_events(calendar_id=calendar_id, max_results=max_results)
            stats["total_fetched"] = len(events)
            
            # Get set of current event IDs from Calendar API (filter out None values)
            current_event_ids: set[str] = {
                event_id for event in events 
                if (event_id := event.get("id")) is not None
            }
            
            # Fetch and process each event
            for event_data in events:
                try:
                    self._process_event(event_data, stats)
                except Exception as e:
                    error_msg = f"Error processing event {event_data.get('id')}: {str(e)}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)
            
            # Remove events from vector store that no longer exist in Calendar
            deleted_count = self._cleanup_deleted_events(current_event_ids)
            stats["deleted_events"] = deleted_count
            
            # Commit all changes
            self.db.commit()
            
            logger.info(
                f"Calendar sync complete for user {self.user.id}: "
                f"{stats['new_events']} new, {stats['updated_events']} updated, "
                f"{stats['deleted_events']} deleted"
            )
            
        except Exception as e:
            error_msg = f"Calendar sync failed for user {self.user.id}: {str(e)}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
            self.db.rollback()
        
        return stats
    
    def _list_events(
        self,
        calendar_id: str = "primary",
        max_results: int = 100
    ) -> list[dict[str, Any]]:
        """List calendar events.
        
        Args:
            calendar_id: Calendar ID
            max_results: Maximum number of events to return
            
        Returns:
            List of event dicts
        """
        events_list: list[dict[str, Any]] = []
        page_token: Optional[str] = None
        
        # Get events from last 60 days to next 90 days
        # This provides context of recent past events and upcoming ones
        from datetime import timedelta
        time_min = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        time_max = (datetime.now(timezone.utc) + timedelta(days=90)).isoformat()
        
        while len(events_list) < max_results:
            try:
                # Call Calendar API with exponential backoff
                # Using timeMin and timeMax to get future events only
                # Using singleEvents=True to expand recurring events into instances
                results = self._api_call_with_retry(
                    lambda: self.service.events().list(
                        calendarId=calendar_id,
                        timeMin=time_min,
                        timeMax=time_max,
                        maxResults=min(2500, max_results - len(events_list)),
                        singleEvents=True,
                        orderBy="startTime",
                        pageToken=page_token
                    ).execute()
                )
                
                events = results.get("items", [])
                events_list.extend(events)
                
                # Check if there are more pages
                page_token = results.get("nextPageToken")
                if not page_token:
                    break
                    
            except HttpError as e:
                logger.error(f"Error listing events: {e}")
                break
        
        return events_list[:max_results]
    
    def _process_event(self, event_data: dict[str, Any], stats: dict[str, Any]) -> None:
        """Process a single calendar event and create/update vector embedding.
        
        Args:
            event_data: Calendar event data from API
            stats: Stats dict to update
        """
        event_id = event_data.get("id")
        if not event_id:
            return
        
        # Check if event already exists (idempotency)
        existing_item = self.db.scalars(
            select(VectorItem).where(
                VectorItem.user_id == self.user.id,
                VectorItem.source_type == "calendar",
                VectorItem.source_id == event_id
            )
        ).first()
        
        # Parse event data
        event_info = self._parse_event(event_data)
        
        # Create text representation for embedding
        text_content = self._format_event_text(event_info)
        
        # Generate embedding
        embedding = self.embedding_service.embed_text(text_content)
        
        if existing_item:
            # Update existing vector item
            existing_item.text = text_content
            existing_item.embedding = embedding
            existing_item.metadata_json = event_info
            stats["updated_events"] += 1
            logger.debug(f"Updated calendar event {event_id}")
        else:
            # Create new vector item
            if not self.user.id:
                raise ValueError("User ID is required")
            
            new_item = VectorItem(
                user_id=self.user.id,
                source_type="calendar",
                source_id=event_id,
                text=text_content,
                embedding=embedding,
                metadata_json=event_info
            )
            self.db.add(new_item)
            stats["new_events"] += 1
            logger.debug(f"Created new calendar event {event_id}")
    
    def _cleanup_deleted_events(self, current_event_ids: set[str]) -> int:
        """Remove calendar events from vector store that no longer exist in Calendar API.
        
        Args:
            current_event_ids: Set of event IDs that currently exist in Calendar
            
        Returns:
            Number of events deleted from vector store
        """
        # Find all calendar events in vector store for this user
        existing_items = self.db.scalars(
            select(VectorItem).where(
                VectorItem.user_id == self.user.id,
                VectorItem.source_type == "calendar"
            )
        ).all()
        
        deleted_count = 0
        for item in existing_items:
            if item.source_id not in current_event_ids:
                # Event no longer exists in Calendar, remove from vector store
                self.db.delete(item)
                deleted_count += 1
                logger.info(f"Removed deleted calendar event {item.source_id} from vector store")
        
        return deleted_count
    
    def _parse_event(self, event_data: dict[str, Any]) -> dict[str, Any]:
        """Parse Calendar event data into structured format.
        
        Args:
            event_data: Raw Calendar API event data
            
        Returns:
            Dict with parsed event fields
        """
        # Extract basic fields
        event_id = event_data.get("id", "")
        summary = event_data.get("summary", "(No Title)")
        description = event_data.get("description", "")
        location = event_data.get("location", "")
        status = event_data.get("status", "")
        
        # Parse start/end times
        start = event_data.get("start", {})
        end = event_data.get("end", {})
        
        start_dt = self._parse_datetime(start)
        end_dt = self._parse_datetime(end)
        
        # Parse attendees
        attendees_raw = event_data.get("attendees", [])
        attendees = [
            {
                "email": a.get("email", ""),
                "name": a.get("displayName", ""),
                "response": a.get("responseStatus", ""),
                "organizer": a.get("organizer", False)
            }
            for a in attendees_raw
        ]
        
        # Parse organizer
        organizer = event_data.get("organizer", {})
        organizer_email = organizer.get("email", "")
        organizer_name = organizer.get("displayName", "")
        
        # Parse recurrence
        recurrence = event_data.get("recurrence", [])
        is_recurring = len(recurrence) > 0
        
        # Parse conferencing
        conference_data = event_data.get("conferenceData", {})
        has_video_call = len(conference_data.get("entryPoints", [])) > 0
        video_link = ""
        if has_video_call:
            entry_points = conference_data.get("entryPoints", [])
            for entry in entry_points:
                if entry.get("entryPointType") == "video":
                    video_link = entry.get("uri", "")
                    break
        
        return {
            "event_id": event_id,
            "summary": summary,
            "description": description,
            "location": location,
            "status": status,
            "start": start_dt.isoformat() if start_dt else None,
            "end": end_dt.isoformat() if end_dt else None,
            "attendees": attendees,
            "organizer_email": organizer_email,
            "organizer_name": organizer_name,
            "is_recurring": is_recurring,
            "recurrence": recurrence,
            "has_video_call": has_video_call,
            "video_link": video_link,
            "html_link": event_data.get("htmlLink", ""),
            "created_at": event_data.get("created", ""),
            "updated_at": event_data.get("updated", ""),
        }
    
    def _parse_datetime(self, datetime_obj: dict[str, Any]) -> Optional[datetime]:
        """Parse Calendar API datetime object.
        
        Args:
            datetime_obj: Dict with 'dateTime' or 'date' field
            
        Returns:
            datetime object or None
        """
        # Try dateTime first (for events with specific times)
        if "dateTime" in datetime_obj:
            try:
                return datetime.fromisoformat(datetime_obj["dateTime"].replace("Z", "+00:00"))
            except (ValueError, AttributeError) as e:
                logger.warning(f"Could not parse dateTime: {datetime_obj.get('dateTime')}, error: {e}")
        
        # Try date (for all-day events)
        if "date" in datetime_obj:
            try:
                date_str = datetime_obj["date"]
                return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except (ValueError, AttributeError) as e:
                logger.warning(f"Could not parse date: {datetime_obj.get('date')}, error: {e}")
        
        return None
    
    def _format_event_text(self, event_info: dict[str, Any]) -> str:
        """Format event info into text for embedding.
        
        Args:
            event_info: Parsed event information
            
        Returns:
            Formatted text string
        """
        parts = []
        
        # Title
        parts.append(f"Event: {event_info['summary']}")
        
        # Time
        if event_info.get("start") and event_info.get("end"):
            start_dt = datetime.fromisoformat(event_info["start"])
            end_dt = datetime.fromisoformat(event_info["end"])
            
            # Format dates
            start_str = start_dt.strftime("%B %d, %Y at %I:%M %p")
            
            # Check if same day
            if start_dt.date() == end_dt.date():
                end_str = end_dt.strftime("%I:%M %p")
                parts.append(f"When: {start_str} to {end_str}")
            else:
                end_str = end_dt.strftime("%B %d, %Y at %I:%M %p")
                parts.append(f"When: {start_str} to {end_str}")
        
        # Location
        if event_info.get("location"):
            parts.append(f"Location: {event_info['location']}")
        
        # Video call
        if event_info.get("has_video_call") and event_info.get("video_link"):
            parts.append(f"Video call: {event_info['video_link']}")
        
        # Description
        if event_info.get("description"):
            # Limit description length
            desc = event_info["description"]
            if len(desc) > 500:
                desc = desc[:500] + "..."
            parts.append(f"Description: {desc}")
        
        # Attendees
        attendees = event_info.get("attendees", [])
        if attendees:
            attendee_names = [
                a.get("name") or a.get("email", "Unknown")
                for a in attendees
                if not a.get("organizer", False)
            ]
            if attendee_names:
                parts.append(f"Attendees: {', '.join(attendee_names)}")
        
        # Organizer
        if event_info.get("organizer_name") or event_info.get("organizer_email"):
            organizer = event_info.get("organizer_name") or event_info.get("organizer_email")
            parts.append(f"Organizer: {organizer}")
        
        # Status
        if event_info.get("status"):
            parts.append(f"Status: {event_info['status']}")
        
        # Recurring
        if event_info.get("is_recurring"):
            parts.append("This is a recurring event")
        
        return "\n".join(parts)
    
    def _api_call_with_retry(
        self,
        func: Any,
        max_retries: int = 5,
        initial_delay: float = 1.0
    ) -> Any:
        """Execute Calendar API call with exponential backoff retry.
        
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
                            f"Calendar API error {e.resp.status}, "
                            f"retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                        continue
                
                # Re-raise if not retryable or max retries reached
                raise
        
        # This should not be reached, but just in case
        raise HttpError(resp={"status": 429}, content=b"Max retries exceeded")
