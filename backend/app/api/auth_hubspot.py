"""HubSpot authentication endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, Cookie, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from ..core.database import engine
from ..models.user import User
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
    state: str = Query(..., description="CSRF state token"),
    error: Optional[str] = Query(None, description="Error from OAuth provider"),
) -> RedirectResponse:
    """Handle HubSpot OAuth callback.
    
    Args:
        code: Authorization code from HubSpot
        state: CSRF state token for validation
        error: Optional error from OAuth provider
        
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
    
    # Verify CSRF state
    state_data = StateManager.verify_state(state)
    if state_data is None:
        logger.warning(f"Invalid or expired state token: {state[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state token",
        )
    
    # Get user ID from state
    user_id = state_data.get("user_id")
    if user_id is None:
        logger.error("No user_id in state data")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state: no user associated",
        )
    
    try:
        # Exchange code for tokens
        token_data = await HubSpotOAuthHelper.exchange_code(code)
        
        logger.info(f"Successfully exchanged HubSpot authorization code for user {user_id}")
        
        # Update user with HubSpot tokens
        with Session(engine) as session:
            user = session.get(User, user_id)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )
            
            user.hubspot_oauth_tokens = token_data
            user.touch()
            session.add(user)
            session.commit()
            logger.info(f"Updated user {user_id} with HubSpot tokens")
        
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
