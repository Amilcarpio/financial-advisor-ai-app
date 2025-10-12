"""Ingestion API endpoints for syncing external data sources."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models.user import User
from app.services.gmail_sync import GmailSyncService
from app.services.calendar_sync import CalendarSyncService
from app.services.hubspot_sync import HubSpotSyncService
from app.services.embedding_pipeline import EmbeddingPipeline
from app.utils.security import get_current_user_from_cookie


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    """Request model for triggering data ingestion."""
    
    source: str = Field(..., description="Data source: 'gmail', 'calendar', or 'hubspot'")
    max_results: int | None = Field(
        default=None,
        description="Max items to ingest (None = all)",
        ge=1,
        le=10000
    )
    gmail_query: str | None = Field(
        default=None,
        description="Gmail query filter (e.g., 'is:unread')"
    )
    calendar_id: str | None = Field(
        default="primary",
        description="Calendar ID to sync (default: 'primary')"
    )


class IngestResponse(BaseModel):
    """Response model for ingestion results."""
    
    status: str = Field(..., description="Status: 'success' or 'error'")
    source: str = Field(..., description="Data source that was ingested")
    message: str = Field(..., description="Human-readable message")
    stats: dict[str, Any] = Field(
        default_factory=dict,
        description="Ingestion statistics"
    )


@router.post("", response_model=IngestResponse)
async def ingest_data(
    request: IngestRequest,
    current_user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_session)
) -> IngestResponse:
    """Trigger data ingestion from external source.
    
    **Gmail Requirements:**
    - User must have valid Google OAuth tokens
    - Tokens must not be expired (refresh handled automatically)
    - Optional: Provide gmail_query to filter messages
    
    **HubSpot Requirements:**
    - User must have valid HubSpot OAuth tokens
    - Tokens must not be expired
    
    Returns:
        IngestResponse with status and statistics
        
    Raises:
        HTTPException: If source is invalid or OAuth tokens are missing
    """
    logger.info(
        f"Ingest request for {request.source} by user {current_user.id}"
    )
    
    try:
        if request.source == "gmail":
            return await _ingest_gmail(request, current_user, db)
        elif request.source == "calendar":
            return await _ingest_calendar(request, current_user, db)
        elif request.source == "hubspot":
            return await _ingest_hubspot(request, current_user, db)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid source: {request.source}. "
                       f"Must be 'gmail', 'calendar', or 'hubspot'."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingestion failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}"
        )


async def _ingest_gmail(
    request: IngestRequest,
    user: User,
    db: Session
) -> IngestResponse:
    """Ingest Gmail messages.
    
    Args:
        request: Ingest request
        user: Current user
        db: Database session
        
    Returns:
        IngestResponse with Gmail sync statistics
        
    Raises:
        HTTPException: If OAuth tokens are missing
    """
    # Check OAuth tokens
    if not user.google_oauth_tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth tokens not found. "
                   "Please authenticate with Google first."
        )
    
    # Initialize Gmail sync service
    gmail_service = GmailSyncService(user=user, db=db)
    
    # Run sync (sync methods are not async)
    stats = gmail_service.sync(
        max_results=request.max_results or 100,
        query=request.gmail_query or ""
    )
    
    # Generate embeddings for the synced emails
    logger.info(f"Generating embeddings for user {user.id}")
    embedding_pipeline = EmbeddingPipeline(db=db)
    embedding_stats = embedding_pipeline.process_emails(user_id=user.id)
    
    # Merge stats
    stats.update({
        "embeddings_generated": embedding_stats.get("total_vectors", 0),
        "chunks_created": embedding_stats.get("total_chunks", 0),
        "embedding_errors": embedding_stats.get("errors", 0)
    })
    
    # Build response
    return IngestResponse(
        status="success",
        source="gmail",
        message=(
            f"Gmail sync complete. "
            f"Fetched {stats['total_fetched']} messages, "
            f"created {stats['new_emails']} new emails, "
            f"updated {stats['updated_emails']} existing emails. "
            f"Generated {stats['embeddings_generated']} embeddings."
        ),
        stats=stats
    )


async def _ingest_calendar(
    request: IngestRequest,
    user: User,
    db: Session
) -> IngestResponse:
    """Ingest Google Calendar events.
    
    Args:
        request: Ingest request
        user: Current user
        db: Database session
        
    Returns:
        IngestResponse with Calendar sync statistics
        
    Raises:
        HTTPException: If OAuth tokens are missing
    """
    # Check OAuth tokens
    if not user.google_oauth_tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth tokens not found. "
                   "Please authenticate with Google first."
        )
    
    # Initialize Calendar sync service
    calendar_service = CalendarSyncService(user=user, db=db)
    
    # Run sync (sync methods are not async)
    stats = calendar_service.sync(
        max_results=request.max_results or 100,
        calendar_id=request.calendar_id or "primary"
    )
    
    # Build response (embeddings are generated directly in the sync service)
    return IngestResponse(
        status="success",
        source="calendar",
        message=(
            f"Calendar sync complete. "
            f"Fetched {stats['total_fetched']} events, "
            f"created {stats['new_events']} new events, "
            f"updated {stats['updated_events']} existing events."
        ),
        stats=stats
    )


async def _ingest_hubspot(
    request: IngestRequest,
    user: User,
    db: Session
) -> IngestResponse:
    """Ingest HubSpot contacts.
    
    Args:
        request: Ingest request
        user: Current user
        db: Database session
        
    Returns:
        IngestResponse with HubSpot sync statistics
        
    Raises:
        HTTPException: If OAuth tokens are missing
    """
    # Check OAuth tokens
    if not user.hubspot_oauth_tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="HubSpot OAuth tokens not found. "
                   "Please authenticate with HubSpot first."
        )
    
    # Initialize HubSpot sync service
    hubspot_service = HubSpotSyncService(user=user, db=db)
    
    # Run sync (sync methods are not async)
    stats = hubspot_service.sync(max_results=request.max_results or 100)
    
    # Generate embeddings for the synced contacts
    logger.info(f"Generating embeddings for HubSpot contacts for user {user.id}")
    embedding_pipeline = EmbeddingPipeline(db=db)
    embedding_stats = embedding_pipeline.process_contacts(user_id=user.id)
    
    # Merge stats
    stats.update({
        "embeddings_generated": embedding_stats.get("total_vectors", 0),
        "chunks_created": embedding_stats.get("total_chunks", 0),
        "embedding_errors": embedding_stats.get("errors", 0)
    })
    
    # Build response
    return IngestResponse(
        status="success",
        source="hubspot",
        message=(
            f"HubSpot sync complete. "
            f"Fetched {stats['total_fetched']} contacts, "
            f"created {stats['new_contacts']} new contacts, "
            f"updated {stats['updated_contacts']} existing contacts. "
            f"Generated {stats['embeddings_generated']} embeddings."
        ),
        stats=stats
    )


@router.get("/status", response_model=dict[str, Any])
async def get_ingest_status(
    current_user: User = Depends(get_current_user_from_cookie)
) -> dict[str, Any]:
    """Get ingestion status for current user.
    
    Returns:
        Dict with OAuth connection status for each source
    """
    return {
        "user_id": current_user.id,
        "gmail_connected": bool(current_user.google_oauth_tokens),
        "calendar_connected": bool(current_user.google_oauth_tokens),
        "hubspot_connected": bool(current_user.hubspot_oauth_tokens)
    }


@router.post("/gmail", response_model=IngestResponse)
async def ingest_gmail_endpoint(
    gmail_query: str | None = None,
    current_user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_session)
) -> IngestResponse:
    """Ingest emails from Gmail.
    
    Args:
        gmail_query: Optional Gmail query string to filter messages
        
    Returns:
        IngestResponse with status and statistics
    """
    request = IngestRequest(source="gmail", gmail_query=gmail_query)
    return await _ingest_gmail(request, current_user, db)


@router.post("/calendar", response_model=IngestResponse)
async def ingest_calendar_endpoint(
    calendar_id: str = "primary",
    max_results: int = 250,
    current_user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_session)
) -> IngestResponse:
    """Ingest events from Google Calendar.
    
    Args:
        calendar_id: Calendar ID to sync (default: 'primary')
        max_results: Maximum number of events to fetch (default: 250)
        
    Returns:
        IngestResponse with status and statistics
    """
    request = IngestRequest(
        source="calendar",
        calendar_id=calendar_id,
        max_results=max_results
    )
    return await _ingest_calendar(request, current_user, db)


@router.post("/hubspot", response_model=IngestResponse)
async def ingest_hubspot_endpoint(
    current_user: User = Depends(get_current_user_from_cookie),
    db: Session = Depends(get_session)
) -> IngestResponse:
    """Ingest contacts from HubSpot.
    
    Returns:
        IngestResponse with status and statistics
    """
    request = IngestRequest(source="hubspot")
    return await _ingest_hubspot(request, current_user, db)
