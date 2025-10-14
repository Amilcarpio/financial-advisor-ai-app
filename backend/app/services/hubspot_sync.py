"""HubSpot synchronization service for ingesting contacts and notes."""
import logging
import time
from datetime import datetime
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models.contact import Contact
from ..models.user import User


logger = logging.getLogger(__name__)


class HubSpotSyncService:
    """Service for syncing HubSpot contacts and notes to the database."""

    BASE_URL = "https://api.hubapi.com"
    
    def __init__(self, user: User, db: Session):
        """Initialize HubSpot sync service.
        
        Args:
            user: User with valid HubSpot OAuth tokens
            db: Database session for storing contacts
        """
        self.user = user
        self.db = db
        self.access_token = self._get_access_token()
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    def _get_access_token(self) -> str:
        """Get HubSpot access token from user's OAuth tokens.
        
        Returns:
            HubSpot access token
            
        Raises:
            ValueError: If user doesn't have valid HubSpot OAuth tokens
        """
        if not self.user.hubspot_oauth_tokens:
            raise ValueError(f"User {self.user.id} has no HubSpot OAuth tokens")
        
        tokens = self.user.hubspot_oauth_tokens
        access_token = tokens.get("access_token")
        
        if not access_token:
            raise ValueError("HubSpot access token not found in user tokens")
        
        return access_token
    
    def __del__(self):
        """Cleanup: close the httpx client when the service is destroyed."""
        try:
            if hasattr(self, 'client') and self.client:
                self.client.close()
        except Exception:
            pass  # Ignore errors during cleanup
    
    def sync(
        self,
        max_results: int = 100,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Sync HubSpot contacts to database.
        
        Args:
            max_results: Maximum number of contacts to fetch
            **kwargs: Additional parameters
            
        Returns:
            Dict with sync statistics:
                - total_fetched: Number of contacts fetched
                - new_contacts: Number of new contacts created
                - updated_contacts: Number of existing contacts updated
                - errors: List of error messages
        """
        stats = {
            "total_fetched": 0,
            "new_contacts": 0,
            "updated_contacts": 0,
            "errors": []
        }
        
        try:
            # List contacts with pagination
            contacts = self._list_contacts(max_results=max_results)
            stats["total_fetched"] = len(contacts)
            
            # Process each contact
            for contact_data in contacts:
                try:
                    self._process_contact(contact_data, stats)
                except Exception as e:
                    contact_id = contact_data.get("id", "unknown")
                    error_msg = f"Error processing contact {contact_id}: {str(e)}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)
            
            # Commit all changes
            self.db.commit()
            
            logger.info(
                f"HubSpot sync complete for user {self.user.id}: "
                f"{stats['new_contacts']} new, {stats['updated_contacts']} updated"
            )
            
        except Exception as e:
            error_msg = f"HubSpot sync failed for user {self.user.id}: {str(e)}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
            self.db.rollback()
        
        return stats
    
    def sync_with_notes(
        self,
        max_results: int = 100,
        include_notes: bool = True,
        **kwargs: Any
    ) -> dict[str, Any]:
        """Sync HubSpot contacts and their notes to database and RAG.
        
        Args:
            max_results: Maximum number of contacts to fetch
            include_notes: Whether to sync notes for each contact
            **kwargs: Additional parameters
            
        Returns:
            Dict with sync statistics including notes
        """
        # First sync contacts
        stats = self.sync(max_results=max_results, **kwargs)
        
        # Add notes stats
        stats["total_notes"] = 0
        stats["notes_synced"] = {}
        
        if include_notes:
            # Import here to avoid circular dependency
            from .embedding_pipeline import EmbeddingPipeline
            
            embedding_pipeline = EmbeddingPipeline(db=self.db)
            
            # List contacts with pagination
            contacts = self._list_contacts(max_results=max_results)
            
            for contact_data in contacts:
                contact_id = contact_data.get("id")
                if not contact_id:
                    continue
                    
                try:
                    # Fetch notes for this contact
                    notes = self.sync_contact_notes(contact_id)
                    stats["total_notes"] += len(notes)
                    
                    if notes:
                        # Generate embeddings for notes
                        note_stats = embedding_pipeline.process_contact_notes(
                            user_id=self.user.id,
                            contact_id=contact_id,
                            notes=notes
                        )
                        stats["notes_synced"][contact_id] = note_stats
                        
                        logger.info(
                            f"Synced {len(notes)} notes for contact {contact_id}"
                        )
                except Exception as e:
                    error_msg = f"Error syncing notes for contact {contact_id}: {str(e)}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)
            
            logger.info(
                f"HubSpot notes sync complete: {stats['total_notes']} notes across "
                f"{len(stats['notes_synced'])} contacts"
            )
        
        return stats
    
    def _list_contacts(self, max_results: int = 100) -> list[dict[str, Any]]:
        """List contacts from HubSpot API.
        
        Args:
            max_results: Maximum number of contacts to return
            
        Returns:
            List of contact data dictionaries
        """
        contacts: list[dict[str, Any]] = []
        after: Optional[str] = None
        
        while len(contacts) < max_results:
            try:
                # Build query parameters
                params = {
                    "limit": min(100, max_results - len(contacts)),
                    "properties": [
                        "firstname",
                        "lastname",
                        "email",
                        "phone",
                        "mobilephone",
                        "company",
                        "jobtitle",
                        "website",
                        "city",
                        "state",
                        "zip",
                        "country",
                        "lifecyclestage",
                        "hs_lead_status",
                        "lastcontacted",
                        "notes_last_updated",
                        "hs_all_accessible_team_ids",
                        "hubspot_owner_id"
                    ],
                    "associations": ["notes"]
                }
                
                if after:
                    params["after"] = after
                
                # Call HubSpot API with retry
                response = self._api_call_with_retry(
                    lambda: self.client.get("/crm/v3/objects/contacts", params=params)
                )
                
                if response.status_code != 200:
                    logger.error(f"HubSpot API error: {response.status_code} - {response.text}")
                    break
                
                data = response.json()
                results = data.get("results", [])
                contacts.extend(results)
                
                # Check for next page
                paging = data.get("paging", {})
                after = paging.get("next", {}).get("after")
                
                if not after:
                    break
                    
            except Exception as e:
                logger.error(f"Error listing contacts: {e}")
                break
        
        return contacts[:max_results]
    
    def _process_contact(self, contact_data: dict[str, Any], stats: dict[str, Any]) -> None:
        """Process a single HubSpot contact.
        
        Args:
            contact_data: Raw HubSpot contact data
            stats: Stats dict to update
        """
        hubspot_id = contact_data.get("id")
        if not hubspot_id:
            logger.warning("Contact missing ID, skipping")
            return
        
        # Check if contact already exists (idempotency)
        existing_contact = self.db.scalars(
            select(Contact).where(Contact.hubspot_id == hubspot_id)
        ).first()
        
        # Parse contact data
        parsed_data = self._parse_contact(contact_data)
        
        if existing_contact:
            # Update existing contact
            for key, value in parsed_data.items():
                setattr(existing_contact, key, value)
            existing_contact.last_synced_at = datetime.utcnow()
            stats["updated_contacts"] += 1
            logger.debug(f"Updated contact {hubspot_id}")
        else:
            # Create new contact
            if not self.user.id:
                raise ValueError("User ID is required")
            
            new_contact = Contact(
                user_id=self.user.id,
                hubspot_id=hubspot_id,
                last_synced_at=datetime.utcnow(),
                **parsed_data
            )
            self.db.add(new_contact)
            stats["new_contacts"] += 1
            logger.debug(f"Created new contact {hubspot_id}")
    
    def _parse_contact(self, contact_data: dict[str, Any]) -> dict[str, Any]:
        """Parse HubSpot contact data into Contact model fields.
        
        Args:
            contact_data: Raw HubSpot contact data
            
        Returns:
            Dict with parsed contact fields
        """
        properties = contact_data.get("properties", {})
        
        # Build full name
        firstname = properties.get("firstname", "")
        lastname = properties.get("lastname", "")
        full_name = f"{firstname} {lastname}".strip() or "(No Name)"
        
        # Extract email
        email = properties.get("email", "")
        
        # Parse additional properties
        phone = properties.get("phone")
        company = properties.get("company")
        job_title = properties.get("jobtitle")
        
        # Parse timestamps
        created_at_str = contact_data.get("createdAt")
        updated_at_str = contact_data.get("updatedAt")
        
        try:
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00")) if created_at_str else datetime.utcnow()
        except (ValueError, AttributeError):
            created_at = datetime.utcnow()
        
        try:
            updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00")) if updated_at_str else datetime.utcnow()
        except (ValueError, AttributeError):
            updated_at = datetime.utcnow()
        
        # Store all properties as JSON
        all_properties = {
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
            "phone": phone,
            "company": company,
            "jobtitle": job_title,
            **properties  # Include all raw properties
        }
        
        return {
            "external_source": "hubspot",
            "primary_email": email,
            "first_name": firstname or None,
            "last_name": lastname or None,
            "company": company or None,
            "phone_number": phone or None,
            "properties_json": all_properties,
        }
    
    def _api_call_with_retry(
        self,
        func: Any,
        max_retries: int = 5,
        initial_delay: float = 1.0
    ) -> httpx.Response:
        """Execute HubSpot API call with exponential backoff retry.
        
        Args:
            func: Function to execute (should return httpx Response)
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds (doubles each retry)
            
        Returns:
            HTTP response
            
        Raises:
            httpx.HTTPError: If all retries fail
        """
        delay = initial_delay
        
        for attempt in range(max_retries):
            try:
                response = func()
                
                # Check if we should retry (rate limit or server error)
                if response.status_code in [429, 500, 502, 503, 504]:
                    if attempt < max_retries - 1:
                        # Get retry-after header if available
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                delay = float(retry_after)
                            except ValueError:
                                pass
                        
                        logger.warning(
                            f"HubSpot API error {response.status_code}, "
                            f"retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                        continue
                
                return response
                
            except httpx.HTTPError as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"HubSpot API request failed: {e}, "
                        f"retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise
        
        # This should not be reached, but just in case
        raise httpx.HTTPError("Max retries exceeded")

    def sync_contact_notes(self, contact_id: str) -> list[dict[str, Any]]:
        """Fetch notes for a specific contact from HubSpot.
        
        Args:
            contact_id: HubSpot contact ID
            
        Returns:
            List of note dictionaries with parsed data
        """
        notes: list[dict[str, Any]] = []
        
        try:
            # Get associated notes for this contact
            # HubSpot uses associations to link notes to contacts
            response = self._api_call_with_retry(
                lambda: self.client.get(
                    f"/crm/v3/objects/contacts/{contact_id}/associations/notes"
                )
            )
            
            if response.status_code != 200:
                logger.warning(
                    f"Failed to fetch notes for contact {contact_id}: "
                    f"{response.status_code} {response.text}"
                )
                return notes
            
            associations = response.json().get("results", [])
            note_ids = [assoc.get("id") for assoc in associations if assoc.get("id")]
            
            # Fetch detailed note data
            if note_ids:
                # Batch fetch notes
                for note_id in note_ids:
                    try:
                        note_response = self._api_call_with_retry(
                            lambda: self.client.get(
                                f"/crm/v3/objects/notes/{note_id}",
                                params={
                                    "properties": "hs_note_body,hs_timestamp,hubspot_owner_id"
                                }
                            )
                        )
                        
                        if note_response.status_code == 200:
                            note_data = note_response.json()
                            notes.append(self._parse_note(note_data))
                        else:
                            logger.warning(
                                f"Failed to fetch note {note_id}: "
                                f"{note_response.status_code}"
                            )
                    except Exception as e:
                        logger.error(f"Error fetching note {note_id}: {e}")
                        continue
            
            logger.info(f"Fetched {len(notes)} notes for contact {contact_id}")
            
        except Exception as e:
            logger.error(f"Error fetching notes for contact {contact_id}: {e}")
        
        return notes
    
    def _parse_note(self, note_data: dict[str, Any]) -> dict[str, Any]:
        """Parse HubSpot note data.
        
        Args:
            note_data: Raw HubSpot note data
            
        Returns:
            Dict with parsed note fields
        """
        properties = note_data.get("properties", {})
        
        # Parse timestamp
        timestamp_str = properties.get("hs_timestamp", "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00")) if timestamp_str else datetime.utcnow()
        except (ValueError, AttributeError):
            timestamp = datetime.utcnow()
        
        return {
            "id": note_data.get("id"),
            "body": properties.get("hs_note_body", ""),
            "timestamp": timestamp,
            "owner_id": properties.get("hubspot_owner_id"),
            "created_at": note_data.get("createdAt"),
            "updated_at": note_data.get("updatedAt"),
        }
