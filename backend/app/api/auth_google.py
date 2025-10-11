"""Google authentication endpoints."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

from ..core.database import engine
from ..models.user import User
from ..utils.oauth_helpers import GoogleOAuthHelper
from ..utils.security import StateManager, create_session_token
from ..core.config import settings


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/google", tags=["google-auth"])


@router.get("/start")
async def google_oauth_start(
    user_id: Optional[int] = Query(None, description="Optional user ID if already logged in"),
) -> RedirectResponse:
    """Initiate Google OAuth flow.
    
    Args:
        user_id: Optional user ID to associate with OAuth flow
        
    Returns:
        Redirect to Google OAuth consent page
    """
    try:
        # Generate CSRF state token
        state = StateManager.create_state(user_id=user_id)
        
        # Get authorization URL
        authorization_url, _ = GoogleOAuthHelper.get_authorization_url(state)
        
        logger.info(f"Starting Google OAuth flow with state: {state[:8]}...")
        
        return RedirectResponse(url=authorization_url, status_code=status.HTTP_302_FOUND)
    
    except Exception as e:
        logger.error(f"Failed to start Google OAuth: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate OAuth flow",
        )


@router.get("/callback")
async def google_oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="CSRF state token"),
    error: Optional[str] = Query(None, description="Error from OAuth provider"),
) -> RedirectResponse:
    """Handle Google OAuth callback.
    
    Args:
        code: Authorization code from Google
        state: CSRF state token for validation
        error: Optional error from OAuth provider
        
    Returns:
        Redirect to frontend with session cookie
    """
    # Handle OAuth errors
    if error:
        logger.error(f"Google OAuth error: {error}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/error?error={error}",
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
    
    try:
        # Exchange code for tokens
        token_data = await GoogleOAuthHelper.exchange_code(code, state)
        
        logger.info("Successfully exchanged Google authorization code")
        
        # Get user info from Google
        user_email = await _get_user_email_from_google(token_data["access_token"])
        
        # Create or update user
        with Session(engine) as session:
            user = session.exec(
                select(User).where(User.email == user_email)
            ).first()
            
            if user is None:
                # Create new user
                user = User(
                    email=user_email,
                    google_oauth_tokens=token_data,
                    is_active=True,
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                logger.info(f"Created new user: {user_email}")
            else:
                # Update existing user
                user.google_oauth_tokens = token_data
                user.is_active = True
                user.touch()
                session.add(user)
                session.commit()
                logger.info(f"Updated user: {user_email}")
        
        # Create session token
        if user.id is None:
            raise ValueError("User ID is None after commit")
        
        session_token = create_session_token(user.id)
        
        # Redirect to frontend with session cookie
        response = RedirectResponse(
            url=f"{settings.frontend_url}/auth/success",
            status_code=status.HTTP_302_FOUND,
        )
        
        # Set httpOnly cookie with session token
        response.set_cookie(
            key="session",
            value=session_token,
            httponly=True,
            secure=settings.app_env == "production",  # HTTPS only in production
            samesite="lax",
            max_age=604800,  # 7 days
        )
        
        return response
    
    except ValueError as e:
        logger.error(f"Failed to exchange code: {e}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/error?error=code_exchange_failed",
            status_code=status.HTTP_302_FOUND,
        )
    except Exception as e:
        logger.error(f"Unexpected error in Google OAuth callback: {e}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/error?error=unexpected_error",
            status_code=status.HTTP_302_FOUND,
        )


async def _get_user_email_from_google(access_token: str) -> str:
    """Get user email from Google userinfo endpoint.
    
    Args:
        access_token: Google access token
        
    Returns:
        User email address
        
    Raises:
        ValueError: If unable to get email
    """
    import httpx
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            data = response.json()
            
            email = data.get("email")
            if not email:
                raise ValueError("No email in userinfo response")
            
            return email
    except Exception as e:
        logger.error(f"Failed to get user email from Google: {e}")
        raise ValueError(f"Failed to get user email: {e}")
