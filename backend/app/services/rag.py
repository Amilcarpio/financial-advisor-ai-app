"""Retrieval-augmented generation service for semantic search and context retrieval."""
import logging
from typing import Any

from sqlmodel import Session, select, col
from pgvector.sqlalchemy import Vector

from app.models.vector_item import VectorItem
from app.models.email import Email
from app.models.contact import Contact
from app.services.embeddings import EmbeddingService


logger = logging.getLogger(__name__)


class RAGService:
    """Service for semantic search and context retrieval using pgvector."""
    
    def __init__(
        self,
        db: Session,
        embedding_service: EmbeddingService | None = None,
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ):
        """Initialize RAG service.
        
        Args:
            db: Database session
            embedding_service: Embedding service (default: creates new instance)
            top_k: Number of results to return
            similarity_threshold: Minimum cosine similarity (0-1)
        """
        self.db = db
        self.embedding_service = embedding_service or EmbeddingService()
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
    
    def search(
        self,
        query: str,
        user_id: int,
        source_type: str | None = None,
        top_k: int | None = None
    ) -> list[dict[str, Any]]:
        """Perform semantic search for query.
        
        Args:
            query: Search query text
            user_id: User ID to filter results
            source_type: Optional filter by source type ('email' or 'contact')
            top_k: Number of results (overrides default)
            
        Returns:
            List of search results with text, metadata, and similarity scores
        """
        if not query or not query.strip():
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)
        
        # Use provided top_k or default
        k = top_k or self.top_k
        
        # Build pgvector similarity search using raw SQL for cosine distance
        # pgvector uses <=> operator for cosine distance
        # Cosine similarity = 1 - cosine_distance
        stmt = select(VectorItem).where(
            VectorItem.user_id == user_id
        )
        
        # Add source type filter if specified
        if source_type:
            stmt = stmt.where(VectorItem.source_type == source_type)
        
        # Get all matching vectors (we'll calculate similarity in Python for now)
        # TODO: Use native pgvector operators when SQLModel supports them better
        results = self.db.exec(stmt).all()
        
        # Calculate cosine similarity for each result
        scored_results = []
        for vector_item in results:
            if vector_item.embedding:
                similarity = self._cosine_similarity(
                    query_embedding,
                    vector_item.embedding
                )
                if similarity >= self.similarity_threshold:
                    scored_results.append((vector_item, similarity))
        
        # Sort by similarity descending and take top k
        scored_results.sort(key=lambda x: x[1], reverse=True)
        scored_results = scored_results[:k]
        
        # Format results
        search_results = []
        for vector_item, sim in scored_results:
            result = {
                "text": vector_item.text,
                "similarity": float(sim),
                "source_type": vector_item.source_type,
                "source_id": vector_item.source_id,
                "metadata": vector_item.metadata_json or {},
                "chunk_index": vector_item.chunk_index,
                "created_at": vector_item.created_at.isoformat() if vector_item.created_at else None
            }
            
            # Add source details
            if vector_item.source_type == "email" and vector_item.source_id:
                try:
                    email_id = int(vector_item.source_id)
                    email = self.db.get(Email, email_id)
                    if email:
                        result["email"] = {
                            "subject": email.subject,
                            "sender": email.sender,
                            "received_at": email.received_at.isoformat() if email.received_at else None,
                            "gmail_id": email.gmail_id
                        }
                except (ValueError, TypeError):
                    pass
            
            elif vector_item.source_type == "contact" and vector_item.source_id:
                try:
                    contact_id = int(vector_item.source_id)
                    contact = self.db.get(Contact, contact_id)
                    if contact:
                        full_name = f"{contact.first_name or ''} {contact.last_name or ''}".strip()
                        result["contact"] = {
                            "name": full_name or "Unknown",
                            "email": contact.primary_email,
                            "company": contact.company,
                            "hubspot_id": contact.hubspot_id
                        }
                except (ValueError, TypeError):
                    pass
            
            search_results.append(result)
        
        logger.info(
            f"Search for '{query[:50]}...' returned {len(search_results)} results "
            f"(threshold: {self.similarity_threshold})"
        )
        
        return search_results
    
    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity (0-1)
        """
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def get_context_for_query(
        self,
        query: str,
        user_id: int,
        max_tokens: int = 4000,
        source_type: str | None = None
    ) -> str:
        """Get formatted context string for RAG.
        
        Args:
            query: Search query
            user_id: User ID to filter results
            max_tokens: Maximum tokens for context (approximate)
            source_type: Optional source type filter
            
        Returns:
            Formatted context string
        """
        # Search for relevant chunks
        results = self.search(
            query=query,
            user_id=user_id,
            source_type=source_type,
            top_k=self.top_k
        )
        
        if not results:
            return "No relevant context found."
        
        # Build context string with token budget
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # Rough estimate: 1 token ~= 4 chars
        
        for i, result in enumerate(results):
            # Format result
            source_info = ""
            if "email" in result:
                email = result["email"]
                source_info = (
                    f"From email: '{email['subject']}' "
                    f"from {email['sender']} on {email['received_at']}"
                )
            elif "contact" in result:
                contact = result["contact"]
                source_info = f"From contact: {contact['name']} ({contact['email']})"
            
            chunk_text = result["text"]
            similarity = result["similarity"]
            
            # Format context entry
            entry = f"[Result {i+1}, Similarity: {similarity:.2f}]\n"
            if source_info:
                entry += f"{source_info}\n"
            entry += f"{chunk_text}\n\n"
            
            # Check token budget
            if total_chars + len(entry) > max_chars:
                logger.info(
                    f"Context budget reached at {i+1}/{len(results)} results"
                )
                break
            
            context_parts.append(entry)
            total_chars += len(entry)
        
        context = "".join(context_parts).strip()
        
        logger.debug(f"Generated context: {len(context)} chars from {len(context_parts)} chunks")
        
        return context
    
    def upsert_vector_item(
        self,
        user_id: int,
        text: str,
        embedding: list[float],
        source_type: str,
        source_id: int,
        chunk_index: int = 0,
        metadata: dict[str, Any] | None = None
    ) -> VectorItem:
        """Create or update vector item.
        
        Args:
            user_id: User ID
            text: Chunk text
            embedding: Embedding vector
            source_type: Source type ('email' or 'contact')
            source_id: Source record ID
            chunk_index: Chunk index in source
            metadata: Optional metadata dict
            
        Returns:
            Created or updated VectorItem
        """
        # Convert source_id to string for VectorItem
        source_id_str = str(source_id)
        
        # Check if vector item already exists
        existing = self.db.exec(
            select(VectorItem)
            .where(VectorItem.user_id == user_id)
            .where(VectorItem.source_type == source_type)
            .where(VectorItem.source_id == source_id_str)
            .where(VectorItem.chunk_index == chunk_index)
        ).first()
        
        if existing:
            # Update existing
            existing.text = text
            existing.embedding = embedding
            existing.metadata_json = metadata or {}
            existing.touch()
            self.db.add(existing)
            self.db.commit()
            self.db.refresh(existing)
            logger.debug(f"Updated vector item {existing.id}")
            return existing
        else:
            # Create new
            vector_item = VectorItem(
                user_id=user_id,
                text=text,
                embedding=embedding,
                source_type=source_type,
                source_id=source_id_str,
                chunk_index=chunk_index,
                metadata_json=metadata or {}
            )
            self.db.add(vector_item)
            self.db.commit()
            self.db.refresh(vector_item)
            logger.debug(f"Created vector item {vector_item.id}")
            return vector_item
    
    def delete_vector_items_by_source(
        self,
        user_id: int,
        source_type: str,
        source_id: int
    ) -> int:
        """Delete all vector items for a source.
        
        Args:
            user_id: User ID
            source_type: Source type
            source_id: Source ID
            
        Returns:
            Number of deleted items
        """
        source_id_str = str(source_id)
        
        stmt = select(VectorItem).where(
            VectorItem.user_id == user_id,
            VectorItem.source_type == source_type,
            VectorItem.source_id == source_id_str
        )
        items = self.db.exec(stmt).all()
        
        for item in items:
            self.db.delete(item)
        
        self.db.commit()
        
        logger.info(
            f"Deleted {len(items)} vector items for {source_type} {source_id}"
        )
        
        return len(items)
