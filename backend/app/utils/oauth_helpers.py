"""OAuth 2.0 helper functions for Google and HubSpot integrations."""
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from ..core.config import settings


logger = logging.getLogger(__name__)


# Google OAuth Configuration
GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]

GOOGLE_CLIENT_CONFIG = {
    "web": {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [settings.google_redirect_uri],
    }
}


# HubSpot OAuth Configuration
HUBSPOT_SCOPES = [
    "crm.objects.contacts.read",
    "crm.objects.contacts.write",
    "crm.objects.companies.read",
    "crm.objects.companies.write",
]

HUBSPOT_AUTH_URL = "https://app.hubspot.com/oauth/authorize"
HUBSPOT_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"


class GoogleOAuthHelper:
    """Helper class for Google OAuth operations."""

    @staticmethod
    def create_flow(state: Optional[str] = None) -> Flow:
        """Create a Google OAuth flow instance.
        
        Args:
            state: Optional CSRF state parameter
            
        Returns:
            Configured Flow instance
        """
        flow = Flow.from_client_config(
            GOOGLE_CLIENT_CONFIG,
            scopes=GOOGLE_SCOPES,
            redirect_uri=settings.google_redirect_uri,
        )
        
        if state:
            flow.state = state  # type: ignore[attr-defined]
            
        return flow

    @staticmethod
    def get_authorization_url(state: str) -> tuple[str, str]:
        """Generate Google OAuth authorization URL.
        
        Args:
            state: CSRF state parameter
            
        Returns:
            Tuple of (authorization_url, state)
        """
        flow = GoogleOAuthHelper.create_flow(state)
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",  # Force consent to get refresh token
        )
        return authorization_url, state

    @staticmethod
    async def exchange_code(code: str, state: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from callback
            state: CSRF state parameter
            
        Returns:
            Dictionary with token information
            
        Raises:
            ValueError: If code exchange fails
        """
        try:
            flow = GoogleOAuthHelper.create_flow(state)
            flow.fetch_token(code=code)
            
            credentials = flow.credentials
            
            return {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,  # type: ignore[attr-defined]
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes,
                "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
            }
        except Exception as e:
            logger.error(f"Failed to exchange Google code: {e}")
            raise ValueError(f"Failed to exchange authorization code: {e}")

    @staticmethod
    async def refresh_token(token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Refresh Google access token.
        
        Args:
            token_data: Current token information
            
        Returns:
            Updated token information
            
        Raises:
            ValueError: If token refresh fails
        """
        try:
            credentials = Credentials(
                token=token_data.get("access_token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=token_data.get("scopes"),
            )
            
            credentials.refresh(Request())
            
            return {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes,
                "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
            }
        except Exception as e:
            logger.error(f"Failed to refresh Google token: {e}")
            raise ValueError(f"Failed to refresh access token: {e}")

    @staticmethod
    def build_credentials(token_data: Dict[str, Any]) -> Credentials:
        """Build Google Credentials object from token data.
        
        Args:
            token_data: Token information dictionary
            
        Returns:
            Google Credentials object
        """
        expiry = None
        if token_data.get("expiry"):
            try:
                expiry = datetime.fromisoformat(token_data["expiry"])
            except (ValueError, TypeError):
                pass
        
        return Credentials(
            token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes"),
            expiry=expiry,
        )


class HubSpotOAuthHelper:
    """Helper class for HubSpot OAuth operations."""

    @staticmethod
    def get_authorization_url(state: str) -> str:
        """Generate HubSpot OAuth authorization URL.
        
        Args:
            state: CSRF state parameter
            
        Returns:
            Authorization URL
        """
        params = {
            "client_id": settings.hubspot_client_id,
            "redirect_uri": settings.hubspot_redirect_uri,
            "scope": " ".join(HUBSPOT_SCOPES),
            "state": state,
        }
        
        param_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{HUBSPOT_AUTH_URL}?{param_string}"

    @staticmethod
    async def exchange_code(code: str) -> Dict[str, Any]:
        """Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from callback
            
        Returns:
            Dictionary with token information
            
        Raises:
            ValueError: If code exchange fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    HUBSPOT_TOKEN_URL,
                    data={
                        "grant_type": "authorization_code",
                        "client_id": settings.hubspot_client_id,
                        "client_secret": settings.hubspot_client_secret,
                        "redirect_uri": settings.hubspot_redirect_uri,
                        "code": code,
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                # Calculate expiry time
                expiry = None
                if data.get("expires_in"):
                    expiry = (datetime.utcnow() + timedelta(seconds=data["expires_in"])).isoformat()
                
                return {
                    "access_token": data.get("access_token"),
                    "refresh_token": data.get("refresh_token"),
                    "expires_in": data.get("expires_in"),
                    "expiry": expiry,
                    "token_type": data.get("token_type"),
                }
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to exchange HubSpot code: {e.response.text}")
            raise ValueError(f"Failed to exchange authorization code: {e}")
        except Exception as e:
            logger.error(f"Failed to exchange HubSpot code: {e}")
            raise ValueError(f"Failed to exchange authorization code: {e}")

    @staticmethod
    async def refresh_token(token_data: Dict[str, Any]) -> Dict[str, Any]:
        """Refresh HubSpot access token.
        
        Args:
            token_data: Current token information
            
        Returns:
            Updated token information
            
        Raises:
            ValueError: If token refresh fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    HUBSPOT_TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "client_id": settings.hubspot_client_id,
                        "client_secret": settings.hubspot_client_secret,
                        "refresh_token": token_data.get("refresh_token"),
                    },
                )
                response.raise_for_status()
                data = response.json()
                
                # Calculate expiry time
                expiry = None
                if data.get("expires_in"):
                    expiry = (datetime.utcnow() + timedelta(seconds=data["expires_in"])).isoformat()
                
                return {
                    "access_token": data.get("access_token"),
                    "refresh_token": data.get("refresh_token"),
                    "expires_in": data.get("expires_in"),
                    "expiry": expiry,
                    "token_type": data.get("token_type"),
                }
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to refresh HubSpot token: {e.response.text}")
            raise ValueError(f"Failed to refresh access token: {e}")
        except Exception as e:
            logger.error(f"Failed to refresh HubSpot token: {e}")
            raise ValueError(f"Failed to refresh access token: {e}")

