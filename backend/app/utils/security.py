"""Security related helpers."""
import secrets
import json
import os
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Any, Dict, Optional
import logging

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..core.config import settings
from ..core.database import get_session
from ..core.security import PII_PATTERNS  # Re-export for convenience
from ..models.user import User

logger = logging.getLogger(__name__)


security = HTTPBearer()


def hash_secret(raw: str) -> str:
    """Naive hashing helper for placeholder implementations."""
    return sha256(raw.encode("utf-8")).hexdigest()


def generate_state_token() -> str:
    """Generate a secure random state token for CSRF protection.
    
    Returns:
        Random URL-safe string
    """
    return secrets.token_urlsafe(32)


def create_session_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT session token for a user.
    
    Args:
        user_id: User ID to encode in token
        expires_delta: Optional expiration time delta (default: 7 days)
        
    Returns:
        Encoded JWT token
    """
    if expires_delta is None:
        expires_delta = timedelta(days=7)
    
    expire = datetime.utcnow() + expires_delta
    
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "session",
    }
    
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def verify_session_token(token: str) -> int:
    """Verify and decode a session token.
    
    Args:
        token: JWT token to verify
        
    Returns:
        User ID from token
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        
        if payload.get("type") != "session":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        
        return int(user_id)
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.JWTError:  # type: ignore[attr-defined]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate token",
        )


class StateManager:
    """Manages CSRF state tokens for OAuth flows.
    
    WARNING: Current implementation uses local file storage which is NOT suitable
    for production environments. In production, replace this with:
    - Redis for distributed state management
    - Database table with TTL/expiration
    - Cloud-based session storage (AWS ElastiCache, etc.)
    
    Security considerations:
    - States should expire after 10 minutes
    - States should be single-use (delete after verification)
    - File permissions must be restricted (600)
    """
    
    _states_file = "/tmp/oauth_states.json"  # INSECURE - use Redis in production!
    
    @classmethod
    def _load_states(cls) -> Dict[str, Dict[str, Any]]:
        """Load states from disk at startup."""
        if os.path.exists(cls._states_file):
            try:
                with open(cls._states_file, 'r') as f:
                    data = json.load(f)
                    # Convert ISO format strings back to datetime objects
                    for state_data in data.values():
                        if "expiry" in state_data and isinstance(state_data["expiry"], str):
                            state_data["expiry"] = datetime.fromisoformat(state_data["expiry"])
                        if "created_at" in state_data and isinstance(state_data["created_at"], str):
                            state_data["created_at"] = datetime.fromisoformat(state_data["created_at"])
                    return data
            except Exception as e:
                logger.error(f"Error loading OAuth states: {e}", exc_info=True)
        return {}
    
    @classmethod
    def _save_states(cls, states: Dict[str, Dict[str, Any]]) -> None:
        """Persist states to disk."""
        try:
            # Convert datetime objects to ISO format strings for JSON serialization
            serializable_states = {}
            for key, state_data in states.items():
                serializable_data = state_data.copy()
                if "expiry" in serializable_data and isinstance(serializable_data["expiry"], datetime):
                    serializable_data["expiry"] = serializable_data["expiry"].isoformat()
                if "created_at" in serializable_data and isinstance(serializable_data["created_at"], datetime):
                    serializable_data["created_at"] = serializable_data["created_at"].isoformat()
                serializable_states[key] = serializable_data
            
            with open(cls._states_file, 'w') as f:
                json.dump(serializable_states, f)
        except Exception as e:
            logger.error(f"Error saving OAuth states: {e}", exc_info=True)
    
    @classmethod
    def create_state(cls, user_id: Optional[int] = None, ttl_seconds: int = 600) -> str:
        """Create and store a new state token.
        
        Args:
            user_id: Optional user ID to associate with state
            ttl_seconds: Time-to-live in seconds (default: 10 minutes)
            
        Returns:
            Generated state token
        """
        state = generate_state_token()
        expiry = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        
        states = cls._load_states()
        states[state] = {
            "user_id": user_id,
            "expiry": expiry,
            "created_at": datetime.utcnow(),
        }
        
        # Cleanup expired states
        cls._cleanup_expired(states)
        cls._save_states(states)
        
        return state
    
    @classmethod
    def verify_state(cls, state: str, remove: bool = True) -> Optional[Dict[str, Any]]:
        """Verify a state token and optionally remove it.
        
        Args:
            state: State token to verify
            remove: Whether to remove the state after verification (default: True)
            
        Returns:
            State data if valid, None otherwise
        """
        states = cls._load_states()
        cls._cleanup_expired(states)
        
        state_data = states.get(state)
        
        if state_data is None:
            cls._save_states(states)
            return None
        
        if datetime.utcnow() > state_data["expiry"]:
            if remove:
                states.pop(state, None)
            cls._save_states(states)
            return None
        
        if remove:
            states.pop(state, None)
        
        cls._save_states(states)
        return state_data
    
    @classmethod
    def _cleanup_expired(cls, states: Dict[str, Dict[str, Any]]) -> None:
        """Remove expired states from storage."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, data in states.items()
            if now > data["expiry"]
        ]
        for key in expired_keys:
            states.pop(key, None)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session)
) -> User:
    """Get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP authorization credentials with JWT token
        db: Database session
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    user_id = verify_session_token(token)
    
    user = db.scalars(select(User).where(User.id == user_id)).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user


async def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_session)
) -> Optional[User]:
    """Get current authenticated user from JWT token in cookie, or None if not authenticated.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        Current user or None if not authenticated
    """
    # Get session token from httpOnly cookie
    session_token = request.cookies.get("session")
    
    if not session_token:
        return None
        
    try:
        user_id = verify_session_token(session_token)
        user = db.scalars(select(User).where(User.id == user_id)).first()
        return user
    except Exception:
        # Token invalid, expired, or user not found
        return None


async def get_current_user_from_cookie(
    request: Request,
    db: Session = Depends(get_session)
) -> User:
    """Get current authenticated user from JWT token in cookie.
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        Current user
        
    Raises:
        HTTPException: If not authenticated or user not found
    """
    user = await get_current_user_optional(request, db)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated"
        )
    
    return user
