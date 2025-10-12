"""Embeddings API endpoints for generating and managing vector embeddings."""
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models.user import User
from app.services.embedding_pipeline import EmbeddingPipeline
from app.utils.security import get_current_user_from_cookie


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/embeddings", tags=["embeddings"])


class GenerateEmbeddingsRequest(BaseModel):
    """Request model for generating embeddings."""
    
    source_type: str = Field(
        default="all",
        description="Data source: 'emails', 'contacts', or 'all'"
    )
    batch_size: int = Field(
        default=50,
        description="Batch size for embedding generation",
        ge=1,
        le=100
    )


class GenerateEmbeddingsResponse(BaseModel):
    """Response model for embedding generation."""
    
    status: str = Field(..., description="Status: 'success' or 'error'")
    message: str = Field(..., description="Human-readable message")
    stats: dict[str, Any] = Field(
        default_factory=dict,
        description="Generation statistics"
    )


class SearchRequest(BaseModel):
    """Request model for semantic search."""
    query: str = Field(..., description="Search query text")
    source_type: Optional[str] = Field(
        default=None,
        description="Optional filter by source type"
    )
    top_k: int = Field(
        default=5,
        description="Number of results to return",
        ge=1,
        le=20
    )


@router.post("/generate", response_model=GenerateEmbeddingsResponse)
async def generate_embeddings(
    request: GenerateEmbeddingsRequest,
    current_user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_session)
) -> GenerateEmbeddingsResponse:
    """Generate embeddings for user's ingested data.
    
    This endpoint processes emails and/or contacts, chunks the text,
    generates embeddings using OpenAI, and stores them in pgvector
    for semantic search.
    
    **Requirements:**
    - User must have ingested data (emails and/or contacts)
    - OpenAI API key must be configured
    
    **Process:**
    1. Fetch emails/contacts from database
    2. Chunk text into 1000-token pieces with 200-token overlap
    3. Generate embeddings in batches using OpenAI
    4. Store vectors in VectorItem table with pgvector
    
    Returns:
        GenerateEmbeddingsResponse with statistics
        
    Raises:
        HTTPException: If source_type is invalid or processing fails
    """
    if not current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID is required"
        )
    
    logger.info(
        f"Embedding generation request for user {current_user.id}, "
        f"source: {request.source_type}"
    )
    
    try:
        # Initialize pipeline
        pipeline = EmbeddingPipeline(db=db)
        
        # Generate embeddings based on source type
        if request.source_type == "emails":
            stats = pipeline.process_emails(
                user_id=current_user.id,
                batch_size=request.batch_size
            )
            message = (
                f"Processed {stats['total_emails']} emails -> "
                f"{stats['total_chunks']} chunks -> "
                f"{stats['total_vectors']} vectors"
            )
        
        elif request.source_type == "contacts":
            stats = pipeline.process_contacts(
                user_id=current_user.id,
                batch_size=request.batch_size
            )
            message = (
                f"Processed {stats['total_contacts']} contacts -> "
                f"{stats['total_chunks']} chunks -> "
                f"{stats['total_vectors']} vectors"
            )
        
        elif request.source_type == "all":
            stats = pipeline.process_all(
                user_id=current_user.id,
                batch_size=request.batch_size
            )
            message = (
                f"Processed {stats['total_items']} items -> "
                f"{stats['total_chunks']} chunks -> "
                f"{stats['total_vectors']} vectors"
            )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid source_type: {request.source_type}. "
                       f"Must be 'emails', 'contacts', or 'all'."
            )
        
        # Check for errors
        if request.source_type == "all":
            error_count = stats.get("total_errors", 0)
        else:
            error_count = stats.get("errors", 0)
        
        if error_count > 0:
            message += f" ({error_count} errors)"
        
        return GenerateEmbeddingsResponse(
            status="success",
            message=message,
            stats=stats
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding generation failed: {str(e)}"
        )


@router.get("/stats", response_model=dict[str, Any])
async def get_embedding_stats(
    current_user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_session)
) -> dict[str, Any]:
    """Get embedding statistics for current user.
    
    Returns counts of vector items by source type.
    
    Returns:
        Dict with vector counts and statistics
    """
    if not current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID is required"
        )
    
    from sqlalchemy import select, func
    from app.models.vector_item import VectorItem
    
    # Count total vectors - use * for count since id is string
    total_vectors = db.scalars(
        select(func.count()).select_from(VectorItem)
        .where(VectorItem.user_id == current_user.id)
    ).first() or 0
    
    # Count by source type
    email_vectors = db.scalars(
        select(func.count()).select_from(VectorItem)
        .where(VectorItem.user_id == current_user.id)
        .where(VectorItem.source_type == "email")
    ).first() or 0
    
    contact_vectors = db.scalars(
        select(func.count()).select_from(VectorItem)
        .where(VectorItem.user_id == current_user.id)
        .where(VectorItem.source_type == "contact")
    ).first() or 0
    
    return {
        "user_id": current_user.id,
        "total_vectors": total_vectors,
        "email_vectors": email_vectors,
        "contact_vectors": contact_vectors
    }


@router.post("/search")
async def search_vectors(
    request: SearchRequest,
    current_user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_session)
) -> dict[str, Any]:
    """Perform semantic search over user's vector embeddings.
    
    Args:
        request: Search request with query, source_type, and top_k
        
    Returns:
        Dict with search results and metadata
    """
    if not current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID is required"
        )
    
    if not request.query or not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty"
        )
    
    try:
        from app.services.rag import RAGService
        
        rag_service = RAGService(db=db, top_k=request.top_k)
        
        results = rag_service.search(
            query=request.query,
            user_id=current_user.id,
            source_type=request.source_type,
            top_k=request.top_k
        )
        
        return {
            "query": request.query,
            "total_results": len(results),
            "results": results
        }
    
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
