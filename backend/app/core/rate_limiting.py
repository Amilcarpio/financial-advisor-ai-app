"""
Rate limiting for API endpoints.

Uses SlowAPI for rate limiting with in-memory or Redis backend.
"""

import logging
from typing import Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from app.core.config import settings

logger = logging.getLogger(__name__)

# Rate limit configurations
DEFAULT_RATE_LIMIT = "100/minute"  # General API endpoints
AUTH_RATE_LIMIT = "10/minute"  # Authentication endpoints
CHAT_RATE_LIMIT = "20/minute"  # Chat/AI endpoints (expensive)
WEBHOOK_RATE_LIMIT = "100/minute"  # Webhook endpoints
TOOL_RATE_LIMIT = "30/minute"  # Tool execution endpoints


def get_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.
    
    Priority:
    1. User ID from JWT (if authenticated)
    2. IP address (for unauthenticated requests)
    """
    # Try to get user from request state (set by auth middleware)
    if hasattr(request.state, 'user') and request.state.user:
        user_id = getattr(request.state.user, 'id', None)
        if user_id:
            return f"user:{user_id}"
    
    # Fall back to IP address
    return get_remote_address(request)


# Initialize rate limiter
# For production with multiple instances, use Redis:
# limiter = Limiter(
#     key_func=get_identifier,
#     storage_uri="redis://localhost:6379"
# )
limiter = Limiter(
    key_func=get_identifier,
    default_limits=[DEFAULT_RATE_LIMIT]
)


def setup_rate_limiting(app) -> None:
    """
    Configure rate limiting for FastAPI app.
    
    Args:
        app: FastAPI application instance
    """
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info("Rate limiting configured with SlowAPI")


# Rate limiting decorators for convenience
def rate_limit_default():
    """Default rate limit decorator."""
    return limiter.limit(DEFAULT_RATE_LIMIT)


def rate_limit_auth():
    """Auth endpoint rate limit decorator."""
    return limiter.limit(AUTH_RATE_LIMIT)


def rate_limit_chat():
    """Chat endpoint rate limit decorator."""
    return limiter.limit(CHAT_RATE_LIMIT)


def rate_limit_webhook():
    """Webhook endpoint rate limit decorator."""
    return limiter.limit(WEBHOOK_RATE_LIMIT)


def rate_limit_tool():
    """Tool endpoint rate limit decorator."""
    return limiter.limit(TOOL_RATE_LIMIT)


# OpenAI API rate limiting (separate from HTTP rate limiting)
class OpenAIRateLimiter:
    """
    Rate limiter for OpenAI API calls to control costs.
    
    Tracks:
    - Requests per user per hour
    - Total tokens per user per day
    - Global budget limits
    """
    
    def __init__(self):
        # In-memory storage (use Redis in production)
        self._user_requests: dict[int, list[float]] = {}
        self._user_tokens: dict[int, list[tuple[float, int]]] = {}
        self._global_tokens: list[tuple[float, int]] = []
        
        # Limits
        self.max_requests_per_user_per_hour = 100
        self.max_tokens_per_user_per_day = 100000  # ~$0.10 per user per day
        self.max_tokens_global_per_day = 1000000  # ~$1.00 per day
    
    def check_user_request_limit(self, user_id: int) -> bool:
        """Check if user has exceeded request rate limit."""
        import time
        now = time.time()
        hour_ago = now - 3600
        
        # Clean old entries
        if user_id in self._user_requests:
            self._user_requests[user_id] = [
                t for t in self._user_requests[user_id] if t > hour_ago
            ]
        else:
            self._user_requests[user_id] = []
        
        # Check limit
        if len(self._user_requests[user_id]) >= self.max_requests_per_user_per_hour:
            logger.warning(
                f"User {user_id} exceeded OpenAI request rate limit: "
                f"{len(self._user_requests[user_id])} requests in last hour"
            )
            return False
        
        # Record request
        self._user_requests[user_id].append(now)
        return True
    
    def check_user_token_limit(self, user_id: int, tokens: int) -> bool:
        """Check if user has exceeded daily token limit."""
        import time
        now = time.time()
        day_ago = now - 86400
        
        # Clean old entries
        if user_id in self._user_tokens:
            self._user_tokens[user_id] = [
                (t, tok) for t, tok in self._user_tokens[user_id] if t > day_ago
            ]
        else:
            self._user_tokens[user_id] = []
        
        # Calculate tokens used today
        tokens_today = sum(tok for _, tok in self._user_tokens[user_id])
        
        # Check limit
        if tokens_today + tokens > self.max_tokens_per_user_per_day:
            logger.warning(
                f"User {user_id} exceeded OpenAI token limit: "
                f"{tokens_today + tokens} tokens (limit: {self.max_tokens_per_user_per_day})"
            )
            return False
        
        # Record tokens
        self._user_tokens[user_id].append((now, tokens))
        return True
    
    def check_global_token_limit(self, tokens: int) -> bool:
        """Check if global daily token limit has been exceeded."""
        import time
        now = time.time()
        day_ago = now - 86400
        
        # Clean old entries
        self._global_tokens = [
            (t, tok) for t, tok in self._global_tokens if t > day_ago
        ]
        
        # Calculate tokens used today
        tokens_today = sum(tok for _, tok in self._global_tokens)
        
        # Check limit
        if tokens_today + tokens > self.max_tokens_global_per_day:
            logger.error(
                f"Global OpenAI token limit exceeded: "
                f"{tokens_today + tokens} tokens (limit: {self.max_tokens_global_per_day})"
            )
            return False
        
        # Record tokens
        self._global_tokens.append((now, tokens))
        return True


# Global OpenAI rate limiter instance
openai_rate_limiter = OpenAIRateLimiter()
