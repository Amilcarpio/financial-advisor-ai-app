"""HubSpot authentication endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, Cookie, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..core.database import engine
from ..models.user import User
from ..services.hubspot_sync import HubSpotSyncService
from ..services.embedding_pipeline import EmbeddingPipeline
from ..utils.oauth_helpers import HubSpotOAuthHelper
from ..utils.security import StateManager, verify_session_token
from ..core.config import settings


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/hubspot", tags=["hubspot-auth"])


@router.get("/start")
async def hubspot_oauth_start(
    session: Optional[str] = Cookie(None, description="Session cookie"),
) -> RedirectResponse:
    """Initiate HubSpot OAuth flow.
    
    Requires user to be already authenticated with Google.
    
    Args:
        session: Session cookie containing user session token
        
    Returns:
        Redirect to HubSpot OAuth consent page
    """
    # Verify user is authenticated
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Must be authenticated with Google first",
        )
    
    try:
        user_id = verify_session_token(session)
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    
    try:
        # Verify user exists
        with Session(engine) as db_session:
            user = db_session.get(User, user_id)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )
        
        # Generate CSRF state token with user ID
        state = StateManager.create_state(user_id=user_id)
        
        # Get authorization URL
        authorization_url = HubSpotOAuthHelper.get_authorization_url(state)
        
        logger.info(f"Starting HubSpot OAuth flow for user {user_id}")
        
        return RedirectResponse(url=authorization_url, status_code=status.HTTP_302_FOUND)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start HubSpot OAuth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate OAuth flow",
        )


@router.get("/callback")
async def hubspot_oauth_callback(
    code: str = Query(..., description="Authorization code from HubSpot"),
    state: Optional[str] = Query(None, description="CSRF state token"),
    error: Optional[str] = Query(None, description="Error from OAuth provider"),
    session: Optional[str] = Cookie(None, description="Session cookie"),
) -> RedirectResponse:
    """Handle HubSpot OAuth callback.
    
    Args:
        code: Authorization code from HubSpot
        state: CSRF state token for validation (optional if session cookie present)
        error: Optional error from OAuth provider
        session: Session cookie containing user session token
        
    Returns:
        Redirect to frontend
    """
    # Handle OAuth errors
    if error:
        logger.error(f"HubSpot OAuth error: {error}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/hubspot/error?error={error}",
            status_code=status.HTTP_302_FOUND,
        )
    
    # Try to get user_id from state first, fall back to session cookie
    user_id = None
    
    if state:
        # Verify CSRF state
        state_data = StateManager.verify_state(state)
        if state_data is None:
            logger.warning(f"Invalid or expired state token: {state[:8]}...")
        else:
            user_id = state_data.get("user_id")
    
    # Fall back to session cookie if state verification failed or no state
    if user_id is None and session:
        try:
            user_id = verify_session_token(session)
            logger.info(f"Using user_id from session cookie: {user_id}")
        except HTTPException:
            pass
    
    if user_id is None:
        logger.error("No valid user_id from state or session")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User authentication required",
        )
    
    try:
        # Exchange code for tokens
        token_data = await HubSpotOAuthHelper.exchange_code(code)
        
        logger.info(f"Successfully exchanged HubSpot authorization code for user {user_id}")
        
        # Get portal ID from HubSpot
        portal_id = await HubSpotOAuthHelper.get_portal_id(token_data["access_token"])
        if portal_id:
            logger.info(f"Retrieved HubSpot portal ID: {portal_id}")
        else:
            logger.warning("Could not retrieve HubSpot portal ID")
        
        # Update user with HubSpot tokens
        with Session(engine) as db_session:
            user = db_session.get(User, user_id)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )
            
            user.hubspot_oauth_tokens = token_data
            if portal_id:
                user.hubspot_portal_id = portal_id
            user.touch()
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            logger.info(f"Updated user {user_id} with HubSpot tokens and portal ID")
            
            # Auto-sync HubSpot contacts and notes in background (fire and forget)
            try:
                logger.info(f"Starting HubSpot auto-sync (with notes) for user {user_id}")
                hubspot_service = HubSpotSyncService(user=user, db=db_session)
                sync_stats = hubspot_service.sync_with_notes(max_results=100, include_notes=True)
                logger.info(f"HubSpot sync_with_notes completed: {sync_stats}")

                # Generate embeddings for synced contacts and notes (embedding pipeline already called inside sync_with_notes for notes)
                embedding_pipeline = EmbeddingPipeline(db=db_session)
                embedding_stats = embedding_pipeline.process_contacts(user_id=user_id)
                logger.info(f"HubSpot embeddings generated: {embedding_stats}")
            except Exception as sync_error:
                # Don't fail the auth flow if sync fails
                logger.error(f"HubSpot auto-sync (with notes) failed (non-fatal): {sync_error}", exc_info=True)
        
        # Redirect to frontend success page
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/hubspot/success",
            status_code=status.HTTP_302_FOUND,
        )
    
    except ValueError as e:
        logger.error(f"Failed to exchange HubSpot code: {e}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/hubspot/error?error=code_exchange_failed",
            status_code=status.HTTP_302_FOUND,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in HubSpot OAuth callback: {e}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/hubspot/error?error=unexpected_error",
            status_code=status.HTTP_302_FOUND,
        )
