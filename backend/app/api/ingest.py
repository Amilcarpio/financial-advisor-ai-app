"""Ingestion API endpoints for syncing external data sources."""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.core.database import get_session
from app.models.user import User
from app.services.gmail_sync import GmailSyncService
from app.services.hubspot_sync import HubSpotSyncService
from app.utils.security import get_current_user


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ingest", tags=["ingest"])


class IngestRequest(BaseModel):
    """Request model for triggering data ingestion."""
    
    source: str = Field(..., description="Data source: 'gmail' or 'hubspot'")
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
    current_user: User = Depends(get_current_user),
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
        elif request.source == "hubspot":
            return await _ingest_hubspot(request, current_user, db)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid source: {request.source}. "
                       f"Must be 'gmail' or 'hubspot'."
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
    
    # Build response
    return IngestResponse(
        status="success",
        source="gmail",
        message=(
            f"Gmail sync complete. "
            f"Fetched {stats['total_fetched']} messages, "
            f"created {stats['new_emails']} new emails, "
            f"updated {stats['updated_emails']} existing emails."
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
    
    # Build response
    return IngestResponse(
        status="success",
        source="hubspot",
        message=(
            f"HubSpot sync complete. "
            f"Fetched {stats['total_fetched']} contacts, "
            f"created {stats['new_contacts']} new contacts, "
            f"updated {stats['updated_contacts']} existing contacts."
        ),
        stats=stats
    )


@router.get("/status", response_model=dict[str, Any])
async def get_ingest_status(
    current_user: User = Depends(get_current_user)
) -> dict[str, Any]:
    """Get ingestion status for current user.
    
    Returns:
        Dict with OAuth connection status for each source
    """
    return {
        "user_id": current_user.id,
        "gmail_connected": bool(current_user.google_oauth_tokens),
        "hubspot_connected": bool(current_user.hubspot_oauth_tokens)
    }


@router.post("/gmail", response_model=IngestResponse)
async def ingest_gmail_endpoint(
    gmail_query: str | None = None,
    current_user: User = Depends(get_current_user),
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


@router.post("/hubspot", response_model=IngestResponse)
async def ingest_hubspot_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
) -> IngestResponse:
    """Ingest contacts from HubSpot.
    
    Returns:
        IngestResponse with status and statistics
    """
    request = IngestRequest(source="hubspot")
    return await _ingest_hubspot(request, current_user, db)
