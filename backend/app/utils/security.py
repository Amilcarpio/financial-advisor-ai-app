"""Security related helpers."""
import secrets
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select

from ..core.config import settings
from ..core.database import get_session
from ..core.security import PII_PATTERNS  # Re-export for convenience
from ..models.user import User


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
    
    In production, this should use Redis or a database.
    For now, we use an in-memory dict.
    """
    
    _states: Dict[str, Dict[str, Any]] = {}
    
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
        
        cls._states[state] = {
            "user_id": user_id,
            "expiry": expiry,
            "created_at": datetime.utcnow(),
        }
        
        # Cleanup expired states
        cls._cleanup_expired()
        
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
        cls._cleanup_expired()
        
        state_data = cls._states.get(state)
        
        if state_data is None:
            return None
        
        if datetime.utcnow() > state_data["expiry"]:
            if remove:
                cls._states.pop(state, None)
            return None
        
        if remove:
            cls._states.pop(state, None)
        
        return state_data
    
    @classmethod
    def _cleanup_expired(cls) -> None:
        """Remove expired states from storage."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, data in cls._states.items()
            if now > data["expiry"]
        ]
        for key in expired_keys:
            cls._states.pop(key, None)


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
    
    user = db.exec(select(User).where(User.id == user_id)).first()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user
