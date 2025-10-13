"""Google authentication endpoints."""
import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..core.database import engine
from ..models.user import User
from ..services.gmail_sync import GmailSyncService
from ..services.calendar_sync import CalendarSyncService
from ..services.embedding_pipeline import EmbeddingPipeline
from ..utils.oauth_helpers import GoogleOAuthHelper, HubSpotOAuthHelper
from ..utils.security import StateManager, create_session_token, get_current_user_optional
from ..core.config import settings


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/google", tags=["google-auth"])

# Common auth router for shared endpoints
auth_router = APIRouter(prefix="/auth", tags=["auth"])


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
        
        logger.info(f"Created state token: {state[:8]}... for user_id: {user_id}")
        
        # Get authorization URL - use the state returned by Google OAuth flow
        authorization_url, actual_state = GoogleOAuthHelper.get_authorization_url(state)
        
        # If Google modified the state, update our stored state
        if actual_state != state:
            logger.warning(f"Google OAuth modified state from {state[:8]}... to {actual_state[:8]}...")
            # Remove old state and store the actual state used by Google
            StateManager.verify_state(state, remove=True)  # Remove old state
            # Manually store the actual state returned by Google
            from ..utils.security import StateManager as SM
            SM._load_states()  # Ensure states are loaded
            states = SM._load_states()
            states[actual_state] = {
                "user_id": user_id,
                "expiry": datetime.utcnow() + timedelta(seconds=600),
                "created_at": datetime.utcnow(),
            }
            SM._save_states(states)
            logger.info(f"Stored modified state: {actual_state[:8]}...")
        
        logger.info(f"Redirecting to Google OAuth with state: {actual_state[:8]}...")
        
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
    logger.info(f"Google OAuth callback received - state: {state[:8]}... code: {code[:20]}...")
    
    # Handle OAuth errors
    if error:
        logger.error(f"Google OAuth error: {error}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/error?error={error}",
            status_code=status.HTTP_302_FOUND,
        )
    
    # Verify CSRF state
    logger.info(f"Verifying state token: {state[:8]}...")
    state_data = StateManager.verify_state(state)
    if state_data is None:
        logger.warning(f"Invalid or expired state token: {state[:8]}...")
        from ..utils.security import StateManager as SM
        states = SM._load_states()
        logger.warning(f"Available states: {list(states.keys())[:3] if states else 'none'}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state token",
        )
    
    try:
        # Exchange code for tokens
        token_data = await GoogleOAuthHelper.exchange_code(code, state)
        
        logger.info("Successfully exchanged Google authorization code")
        
        # Get user info from Google
        user_info = await _get_user_info_from_google(token_data["access_token"])
        user_email = user_info["email"]
        
        # Create or update user
        with Session(engine) as session:
            user = session.scalars(
                select(User).where(User.email == user_email)
            ).first()
            
            if user is None:
                # Create new user
                user = User(
                    email=user_email,
                    full_name=user_info.get("name"),
                    google_oauth_tokens={**token_data, "picture": user_info.get("picture")},
                    is_active=True,
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                logger.info(f"Created new user: {user_email}")
            else:
                # Update existing user
                user.full_name = user_info.get("name")
                user.google_oauth_tokens = {**token_data, "picture": user_info.get("picture")}
                user.is_active = True
                user.touch()
                session.add(user)
                session.commit()
                session.refresh(user)
                logger.info(f"Updated user: {user_email}")
            
            # Save user_id before session closes
            user_id = user.id
            if user_id is None:
                raise ValueError("User ID is None after commit")
            
            # Auto-sync Gmail emails and Calendar events in background
            try:
                logger.info(f"Starting auto-sync for user {user_id}")
                
                # Sync Gmail emails
                gmail_service = GmailSyncService(user=user, db=session)
                gmail_stats = gmail_service.sync(max_results=100, query="")
                logger.info(f"Gmail sync completed: {gmail_stats}")
                
                # Sync Calendar events
                calendar_service = CalendarSyncService(user=user, db=session)
                calendar_stats = calendar_service.sync(max_results=250)
                logger.info(f"Calendar sync completed: {calendar_stats}")
                
                # Generate embeddings for synced emails
                embedding_pipeline = EmbeddingPipeline(db=session)
                embedding_stats = embedding_pipeline.process_emails(user_id=user_id)
                logger.info(f"Embeddings generated: {embedding_stats}")
            except Exception as sync_error:
                # Don't fail the auth flow if sync fails
                logger.error(f"Auto-sync failed (non-fatal): {sync_error}", exc_info=True)
        
        # Create session token (outside of session context)
        session_token = create_session_token(user_id)
        
        logger.info(f"Created session token for user {user_id}, redirecting to {settings.frontend_url}/auth/success")
        
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
            secure=True,
            samesite="none", 
            max_age=604800,
        )
        
        logger.info(f"Set session cookie for user {user_id}")
        
        return response
    
    except Exception as e:
        logger.error(f"Unexpected error in Google OAuth callback: {e}")
        return RedirectResponse(
            url=f"{settings.frontend_url}/auth/error?error=unexpected_error",
            status_code=status.HTTP_302_FOUND,
        )


async def _get_user_info_from_google(access_token: str) -> dict:
    """Get user info from Google userinfo endpoint.
    
    Args:
        access_token: Google access token
        
    Returns:
        Dictionary with user info (email, name, picture)
        
    Raises:
        ValueError: If unable to get user info
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
            
            return {
                "email": email,
                "name": data.get("name"),
                "picture": data.get("picture"),
            }
    except Exception as e:
        logger.error(f"Failed to get user info from Google: {e}")
        raise ValueError(f"Failed to get user info: {e}")

@auth_router.get("/me")
async def get_current_user_info(current_user: Optional[User] = Depends(get_current_user_optional)):
    """Get current authenticated user information.
    
    Returns user info if authenticated, null if not.
    Checks if HubSpot token is valid if present.
    
    Args:
        current_user: Current authenticated user from session (optional)
        
    Returns:
        User information or null if not authenticated
    """
    if current_user is None:
        return {"user": None}
    
    # Get picture from google_oauth_tokens if available
    picture = None
    if current_user.google_oauth_tokens:
        picture = current_user.google_oauth_tokens.get("picture")
    
    # Check if HubSpot token is valid
    hubspot_connected = False
    if current_user.hubspot_oauth_tokens:
        try:
            access_token = current_user.hubspot_oauth_tokens.get("access_token")
            if access_token:
                # Validate token with HubSpot API
                hubspot_connected = await HubSpotOAuthHelper.check_token_valid(access_token)
                if not hubspot_connected:
                    logger.info(f"HubSpot token validation failed for user {current_user.id}")
            else:
                logger.warning(f"User {current_user.id} has hubspot_oauth_tokens but no access_token")
        except Exception as e:
            logger.error(f"Error checking HubSpot token validity for user {current_user.id}: {e}")
            # On error, assume not connected to be safe
            hubspot_connected = False
    
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.full_name,
            "picture": picture,
            "is_active": current_user.is_active,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
            "hubspot_connected": hubspot_connected,
        }
    }


@auth_router.post("/setup-push-notifications")
async def setup_push_notifications(
    current_user: User = Depends(get_current_user_optional)
) -> dict[str, Any]:
    """
    Set up push notifications for Gmail and Calendar.
    
    This endpoint should be called after successful OAuth to enable real-time updates.
    Push notifications expire after 7 days and need to be renewed.
    
    Requires:
        - GOOGLE_PUBSUB_TOPIC: Pub/Sub topic for Gmail (projects/{project}/topics/{topic})
        - WEBHOOK_BASE_URL: Base URL for Calendar webhooks (https://your-domain.com)
    
    Returns:
        Dict with setup status for Gmail and Calendar
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not current_user.google_oauth_tokens:
        raise HTTPException(status_code=400, detail="Google account not connected")
    
    results = {
        "gmail": {"enabled": False, "error": None},
        "calendar": {"enabled": False, "error": None}
    }
    
    with Session(engine) as session:
        user = session.get(User, current_user.id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Setup Gmail push notifications
        if settings.google_pubsub_topic:
            try:
                gmail_service = GmailSyncService(user=user, db=session)
                gmail_response = gmail_service.setup_push_notifications(
                    topic_name=settings.google_pubsub_topic
                )
                results["gmail"]["enabled"] = True
                results["gmail"]["historyId"] = gmail_response.get("historyId")
                results["gmail"]["expiration"] = gmail_response.get("expiration")
            except Exception as e:
                logger.error(f"Failed to setup Gmail push notifications: {e}")
                results["gmail"]["error"] = str(e)
        else:
            results["gmail"]["error"] = "GOOGLE_PUBSUB_TOPIC not configured"
        
        # Setup Calendar push notifications
        if settings.webhook_base_url:
            try:
                calendar_service = CalendarSyncService(user=user, db=session)
                webhook_url = f"{settings.webhook_base_url}/api/webhooks/calendar"
                calendar_response = calendar_service.setup_push_notifications(
                    webhook_url=webhook_url
                )
                results["calendar"]["enabled"] = True
                results["calendar"]["channelId"] = calendar_response.get("id")
                results["calendar"]["resourceId"] = calendar_response.get("resourceId")
                results["calendar"]["expiration"] = calendar_response.get("expiration")
            except Exception as e:
                logger.error(f"Failed to setup Calendar push notifications: {e}")
                results["calendar"]["error"] = str(e)
        else:
            results["calendar"]["error"] = "WEBHOOK_BASE_URL not configured"
    
    return results


@auth_router.post("/logout")
async def logout(response: Response):
    """Logout user by clearing session cookie.
    
    Args:
        response: FastAPI response to set cookie
        
    Returns:
        Success message
    """
    # Must match the same parameters used in set_cookie for proper deletion
    response.delete_cookie(
        key="session",
        httponly=True,
        secure=True,
        samesite="none",
    )
    return {"message": "Logged out successfully"}