"""Embedding generation pipeline for ingested data."""
import logging
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.email import Email
from app.models.contact import Contact
from app.services.embeddings import EmbeddingService
from app.services.rag import RAGService
from app.utils.chunking import TextChunker


logger = logging.getLogger(__name__)


class EmbeddingPipeline:
    """Pipeline for generating embeddings from ingested data."""
    
    def __init__(
        self,
        db: Session,
        embedding_service: EmbeddingService | None = None,
        rag_service: RAGService | None = None,
        chunker: TextChunker | None = None
    ):
        """Initialize embedding pipeline.
        
        Args:
            db: Database session
            embedding_service: Embedding service (default: creates new)
            rag_service: RAG service (default: creates new)
            chunker: Text chunker (default: creates new)
        """
        self.db = db
        self.embedding_service = embedding_service or EmbeddingService()
        self.rag_service = rag_service or RAGService(db=db, embedding_service=self.embedding_service)
        self.chunker = chunker or TextChunker(chunk_size=1000, chunk_overlap=200)
    
    def process_emails(
        self,
        user_id: int,
        email_ids: list[int] | None = None,
        batch_size: int = 50
    ) -> dict[str, Any]:
        """Generate embeddings for emails.
        
        Args:
            user_id: User ID
            email_ids: Optional list of specific email IDs (None = all user emails)
            batch_size: Batch size for embedding generation
            
        Returns:
            Statistics dict with counts
        """
        # Get emails to process
        if email_ids:
            stmt = select(Email).where(
                Email.user_id == user_id,
                Email.id.in_(email_ids)  # type: ignore[attr-defined]
            )
        else:
            stmt = select(Email).where(Email.user_id == user_id)
        
        emails = self.db.scalars(stmt).all()
        
        if not emails:
            logger.info(f"No emails found for user {user_id}")
            return {
                "total_emails": 0,
                "total_chunks": 0,
                "total_vectors": 0,
                "errors": 0
            }
        
        logger.info(f"Processing {len(emails)} emails for user {user_id}")
        
        stats = {
            "total_emails": len(emails),
            "total_chunks": 0,
            "total_vectors": 0,
            "errors": 0
        }
        
        # Process emails in batches
        all_chunks = []
        chunk_metadata = []
        
        for email in emails:
            try:
                # Build email text from subject and body
                email_parts = []
                if email.subject:
                    email_parts.append(f"Subject: {email.subject}")
                if email.sender:
                    email_parts.append(f"From: {email.sender}")
                if email.body_plain:
                    email_parts.append(f"\n{email.body_plain}")
                elif email.snippet:
                    email_parts.append(f"\n{email.snippet}")
                
                email_text = "\n".join(email_parts)
                
                if not email_text.strip():
                    logger.warning(f"Email {email.id} has no content, skipping")
                    continue
                
                # Chunk email text
                chunks = self.chunker.chunk_text(
                    email_text,
                    metadata={
                        "email_id": email.id,
                        "subject": email.subject,
                        "sender": email.sender,
                        "gmail_id": email.gmail_id
                    }
                )
                
                stats["total_chunks"] += len(chunks)
                
                # Collect chunks and metadata for batch processing
                for chunk in chunks:
                    all_chunks.append(chunk["text"])
                    chunk_metadata.append({
                        "email_id": email.id,
                        "chunk_index": chunk["metadata"]["chunk_index"],
                        "metadata": chunk["metadata"]
                    })
            
            except Exception as e:
                logger.error(f"Error processing email {email.id}: {e}", exc_info=True)
                stats["errors"] += 1
        
        # Generate embeddings in batches
        if all_chunks:
            try:
                logger.info(f"Generating embeddings for {len(all_chunks)} chunks")
                embeddings = self.embedding_service.embed_batch(
                    all_chunks,
                    batch_size=batch_size
                )
                
                # Store vector items
                for i, embedding in enumerate(embeddings):
                    meta = chunk_metadata[i]
                    try:
                        self.rag_service.upsert_vector_item(
                            user_id=user_id,
                            text=all_chunks[i],
                            embedding=embedding,
                            source_type="email",
                            source_id=meta["email_id"],
                            chunk_index=meta["chunk_index"],
                            metadata=meta["metadata"]
                        )
                        stats["total_vectors"] += 1
                    except Exception as e:
                        logger.error(f"Error storing vector item: {e}", exc_info=True)
                        stats["errors"] += 1
            
            except Exception as e:
                logger.error(f"Error generating embeddings: {e}", exc_info=True)
                stats["errors"] += len(all_chunks)
        
        logger.info(
            f"Processed {stats['total_emails']} emails -> "
            f"{stats['total_chunks']} chunks -> "
            f"{stats['total_vectors']} vectors "
            f"({stats['errors']} errors)"
        )
        
        return stats
    
    def process_contacts(
        self,
        user_id: int,
        contact_ids: list[int] | None = None,
        batch_size: int = 50
    ) -> dict[str, Any]:
        """Generate embeddings for contacts.
        
        Args:
            user_id: User ID
            contact_ids: Optional list of specific contact IDs (None = all user contacts)
            batch_size: Batch size for embedding generation
            
        Returns:
            Statistics dict with counts
        """
        # Get contacts to process
        if contact_ids:
            stmt = select(Contact).where(
                Contact.user_id == user_id,
                Contact.id.in_(contact_ids)  # type: ignore[attr-defined]
            )
        else:
            stmt = select(Contact).where(Contact.user_id == user_id)
        
        contacts = self.db.scalars(stmt).all()
        
        if not contacts:
            logger.info(f"No contacts found for user {user_id}")
            return {
                "total_contacts": 0,
                "total_chunks": 0,
                "total_vectors": 0,
                "errors": 0
            }
        
        logger.info(f"Processing {len(contacts)} contacts for user {user_id}")
        
        stats = {
            "total_contacts": len(contacts),
            "total_chunks": 0,
            "total_vectors": 0,
            "errors": 0
        }
        
        # Process contacts in batches
        all_chunks = []
        chunk_metadata = []
        
        for contact in contacts:
            try:
                # Build contact text from available fields
                contact_parts = []
                
                # Name
                full_name = f"{contact.first_name or ''} {contact.last_name or ''}".strip()
                if full_name:
                    contact_parts.append(f"Name: {full_name}")
                
                # Email
                if contact.primary_email:
                    contact_parts.append(f"Email: {contact.primary_email}")
                
                # Phone
                if contact.phone_number:
                    contact_parts.append(f"Phone: {contact.phone_number}")
                
                # Company
                if contact.company:
                    contact_parts.append(f"Company: {contact.company}")
                
                # Extract additional fields from properties_json
                if contact.properties_json:
                    job_title = contact.properties_json.get("jobtitle")
                    if job_title:
                        contact_parts.append(f"Job Title: {job_title}")
                    
                    website = contact.properties_json.get("website")
                    if website:
                        contact_parts.append(f"Website: {website}")
                    
                    city = contact.properties_json.get("city")
                    state = contact.properties_json.get("state")
                    country = contact.properties_json.get("country")
                    location_parts = [p for p in [city, state, country] if p]
                    if location_parts:
                        contact_parts.append(f"Location: {', '.join(location_parts)}")
                
                # Lifecycle stage
                if contact.lifecycle_stage:
                    contact_parts.append(f"Lifecycle Stage: {contact.lifecycle_stage}")
                
                # Add remaining properties as JSON text
                if contact.properties_json:
                    # Skip already processed fields
                    skip_keys = {"firstname", "lastname", "email", "phone", "company", 
                                "jobtitle", "website", "city", "state", "country", 
                                "lifecyclestage", "zip"}
                    
                    props_text = "\n".join(
                        f"{key}: {value}"
                        for key, value in contact.properties_json.items()
                        if value and key not in skip_keys
                    )
                    if props_text:
                        contact_parts.append(f"\nAdditional Info:\n{props_text}")
                
                contact_text = "\n".join(contact_parts)
                
                if not contact_text.strip():
                    logger.warning(f"Contact {contact.id} has no content, skipping")
                    continue
                
                # Chunk contact text (usually fits in one chunk)
                chunks = self.chunker.chunk_text(
                    contact_text,
                    metadata={
                        "contact_id": contact.id,
                        "name": full_name,
                        "email": contact.primary_email,
                        "company": contact.company,
                        "hubspot_id": contact.hubspot_id
                    }
                )
                
                stats["total_chunks"] += len(chunks)
                
                # Collect chunks and metadata for batch processing
                for chunk in chunks:
                    all_chunks.append(chunk["text"])
                    chunk_metadata.append({
                        "contact_id": contact.id,
                        "chunk_index": chunk["metadata"]["chunk_index"],
                        "metadata": chunk["metadata"]
                    })
            
            except Exception as e:
                logger.error(f"Error processing contact {contact.id}: {e}", exc_info=True)
                stats["errors"] += 1
        
        # Generate embeddings in batches
        if all_chunks:
            try:
                logger.info(f"Generating embeddings for {len(all_chunks)} chunks")
                embeddings = self.embedding_service.embed_batch(
                    all_chunks,
                    batch_size=batch_size
                )
                
                # Store vector items
                for i, embedding in enumerate(embeddings):
                    meta = chunk_metadata[i]
                    try:
                        self.rag_service.upsert_vector_item(
                            user_id=user_id,
                            text=all_chunks[i],
                            embedding=embedding,
                            source_type="contact",
                            source_id=meta["contact_id"],
                            chunk_index=meta["chunk_index"],
                            metadata=meta["metadata"]
                        )
                        stats["total_vectors"] += 1
                    except Exception as e:
                        logger.error(f"Error storing vector item: {e}", exc_info=True)
                        stats["errors"] += 1
            
            except Exception as e:
                logger.error(f"Error generating embeddings: {e}", exc_info=True)
                stats["errors"] += len(all_chunks)
        
        logger.info(
            f"Processed {stats['total_contacts']} contacts -> "
            f"{stats['total_chunks']} chunks -> "
            f"{stats['total_vectors']} vectors "
            f"({stats['errors']} errors)"
        )
        
        return stats
    
    def process_contact_notes(
        self,
        user_id: int,
        contact_id: str,
        notes: list[dict[str, Any]],
        batch_size: int = 50
    ) -> dict[str, Any]:
        """Generate embeddings for contact notes from HubSpot.
        
        Args:
            user_id: User ID
            contact_id: HubSpot contact ID
            notes: List of parsed note dictionaries from HubSpotSyncService
            batch_size: Batch size for embedding generation
            
        Returns:
            Statistics dict with counts
        """
        if not notes:
            logger.info(f"No notes to process for contact {contact_id}")
            return {
                "total_notes": 0,
                "total_chunks": 0,
                "total_vectors": 0,
                "errors": 0
            }
        
        logger.info(f"Processing {len(notes)} notes for contact {contact_id}")
        
        stats = {
            "total_notes": len(notes),
            "total_chunks": 0,
            "total_vectors": 0,
            "errors": 0
        }
        
        # Process notes in batches
        all_chunks = []
        chunk_metadata = []
        
        for note in notes:
            try:
                note_id = note.get("id")
                note_body = note.get("body", "")
                timestamp = note.get("timestamp")
                
                if not note_body.strip():
                    logger.warning(f"Note {note_id} has no content, skipping")
                    continue
                
                # Build note text with metadata
                timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M') if timestamp else 'Unknown date'
                note_text = f"[HubSpot Note from {timestamp_str}]\n{note_body}"
                
                # Chunk note text
                chunks = self.chunker.chunk_text(
                    note_text,
                    metadata={
                        "note_id": note_id,
                        "contact_id": contact_id,
                        "timestamp": timestamp.isoformat() if timestamp else None,
                        "owner_id": note.get("owner_id")
                    }
                )
                
                stats["total_chunks"] += len(chunks)
                
                # Collect chunks and metadata for batch processing
                for chunk in chunks:
                    all_chunks.append(chunk["text"])
                    chunk_metadata.append({
                        "note_id": note_id,
                        "contact_id": contact_id,
                        "chunk_index": chunk["metadata"]["chunk_index"],
                        "metadata": chunk["metadata"]
                    })
            
            except Exception as e:
                logger.error(f"Error processing note {note.get('id')}: {e}", exc_info=True)
                stats["errors"] += 1
        
        # Generate embeddings in batches
        if all_chunks:
            try:
                logger.info(f"Generating embeddings for {len(all_chunks)} note chunks")
                embeddings = self.embedding_service.embed_batch(
                    all_chunks,
                    batch_size=batch_size
                )
                
                # Store vector items
                for i, embedding in enumerate(embeddings):
                    meta = chunk_metadata[i]
                    try:
                        self.rag_service.upsert_vector_item(
                            user_id=user_id,
                            text=all_chunks[i],
                            embedding=embedding,
                            source_type="hubspot_note",
                            source_id=meta["note_id"],
                            chunk_index=meta["chunk_index"],
                            metadata=meta["metadata"]
                        )
                        stats["total_vectors"] += 1
                    except Exception as e:
                        logger.error(f"Error storing vector item: {e}", exc_info=True)
                        stats["errors"] += 1
            
            except Exception as e:
                logger.error(f"Error generating embeddings: {e}", exc_info=True)
                stats["errors"] += len(all_chunks)
        
        logger.info(
            f"Processed {stats['total_notes']} notes -> "
            f"{stats['total_chunks']} chunks -> "
            f"{stats['total_vectors']} vectors "
            f"({stats['errors']} errors)"
        )
        
        return stats
    
    def process_all(
        self,
        user_id: int,
        batch_size: int = 50
    ) -> dict[str, Any]:
        """Generate embeddings for all user data (emails and contacts).
        
        Args:
            user_id: User ID
            batch_size: Batch size for embedding generation
            
        Returns:
            Combined statistics dict
        """
        logger.info(f"Processing all data for user {user_id}")
        
        # Process emails
        email_stats = self.process_emails(user_id, batch_size=batch_size)
        
        # Process contacts
        contact_stats = self.process_contacts(user_id, batch_size=batch_size)
        
        # Combine stats
        combined_stats = {
            "emails": email_stats,
            "contacts": contact_stats,
            "total_items": (
                email_stats["total_emails"] + 
                contact_stats["total_contacts"]
            ),
            "total_chunks": (
                email_stats["total_chunks"] + 
                contact_stats["total_chunks"]
            ),
            "total_vectors": (
                email_stats["total_vectors"] + 
                contact_stats["total_vectors"]
            ),
            "total_errors": (
                email_stats["errors"] + 
                contact_stats["errors"]
            )
        }
        
        logger.info(
            f"Completed processing for user {user_id}: "
            f"{combined_stats['total_items']} items -> "
            f"{combined_stats['total_vectors']} vectors "
            f"({combined_stats['total_errors']} errors)"
        )
        
        return combined_stats
