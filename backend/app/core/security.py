"""
Security middleware and utilities.

Implements:
- Security headers (CSP, X-Frame-Options, etc.)
- PII redaction from logs
- Input sanitization helpers
"""

import re
from typing import Any, Dict, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    Headers added:
    - Content-Security-Policy: Restricts resource loading
    - X-Frame-Options: Prevents clickjacking
    - X-Content-Type-Options: Prevents MIME sniffing
    - X-XSS-Protection: Enables XSS filter
    - Referrer-Policy: Controls referrer information
    - Permissions-Policy: Controls browser features
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        
        # Content Security Policy - restrict resource loading
        # Note: Adjust for your frontend needs
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://api.openai.com; "
            "frame-ancestors 'none';"
        )
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Control browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        
        return response


class PIIRedactor:
    """
    Redact Personally Identifiable Information (PII) from logs and data.
    
    Patterns redacted:
    - Email addresses
    - Phone numbers
    - Credit card numbers
    - Social Security Numbers
    - OAuth tokens
    """
    
    # Regex patterns for PII
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
    CREDIT_CARD_PATTERN = re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b')
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    TOKEN_PATTERN = re.compile(r'(token|key|secret|password)[\s:=]+["\']?([^"\'\s]+)["\']?', re.IGNORECASE)
    
    @classmethod
    def redact_email(cls, text: str) -> str:
        """Redact email addresses."""
        return cls.EMAIL_PATTERN.sub('[EMAIL_REDACTED]', text)
    
    @classmethod
    def redact_phone(cls, text: str) -> str:
        """Redact phone numbers."""
        return cls.PHONE_PATTERN.sub('[PHONE_REDACTED]', text)
    
    @classmethod
    def redact_credit_card(cls, text: str) -> str:
        """Redact credit card numbers."""
        return cls.CREDIT_CARD_PATTERN.sub('[CC_REDACTED]', text)
    
    @classmethod
    def redact_ssn(cls, text: str) -> str:
        """Redact Social Security Numbers."""
        return cls.SSN_PATTERN.sub('[SSN_REDACTED]', text)
    
    @classmethod
    def redact_tokens(cls, text: str) -> str:
        """Redact tokens, keys, secrets, passwords."""
        return cls.TOKEN_PATTERN.sub(r'\1=[REDACTED]', text)
    
    @classmethod
    def redact_all(cls, text: str) -> str:
        """Apply all redaction rules."""
        text = cls.redact_email(text)
        text = cls.redact_phone(text)
        text = cls.redact_credit_card(text)
        text = cls.redact_ssn(text)
        text = cls.redact_tokens(text)
        return text
    
    @classmethod
    def redact_dict(cls, data: Dict[str, Any], keys_to_redact: Optional[list[str]] = None) -> Dict[str, Any]:
        """
        Redact sensitive keys from dictionary.
        
        Args:
            data: Dictionary to redact
            keys_to_redact: List of keys to redact (default: common sensitive keys)
        
        Returns:
            Dictionary with redacted values
        """
        if keys_to_redact is None:
            keys_to_redact = [
                'password', 'token', 'secret', 'api_key', 'access_token',
                'refresh_token', 'oauth_token', 'authorization', 'cookie',
                'ssn', 'social_security', 'credit_card', 'card_number'
            ]
        
        redacted = data.copy()
        for key in keys_to_redact:
            if key in redacted:
                redacted[key] = '[REDACTED]'
        
        return redacted


class InputSanitizer:
    """
    Sanitize user inputs to prevent injection attacks.
    
    Provides utilities for:
    - HTML sanitization
    - SQL injection prevention (use with ORM)
    - XSS prevention
    """
    
    # HTML tags allowed in user input (very restrictive)
    ALLOWED_HTML_TAGS = ['b', 'i', 'u', 'em', 'strong', 'p', 'br']
    
    # Pattern for detecting potential SQL injection
    SQL_INJECTION_PATTERN = re.compile(
        r'(\bunion\b|\bselect\b|\binsert\b|\bupdate\b|\bdelete\b|\bdrop\b|\bcreate\b)',
        re.IGNORECASE
    )
    
    # Pattern for detecting XSS attempts
    XSS_PATTERN = re.compile(
        r'<script|javascript:|onerror=|onclick=|onload=',
        re.IGNORECASE
    )
    
    @classmethod
    def remove_html_tags(cls, text: str, allowed_tags: Optional[list[str]] = None) -> str:
        """
        Remove HTML tags from text, keeping only allowed tags.
        
        Args:
            text: Input text potentially containing HTML
            allowed_tags: List of allowed HTML tags (default: ALLOWED_HTML_TAGS)
        
        Returns:
            Sanitized text
        """
        if allowed_tags is None:
            allowed_tags = cls.ALLOWED_HTML_TAGS
        
        # Simple implementation - in production use bleach or html-sanitizer
        # For now, remove all tags
        import html
        return html.escape(text)
    
    @classmethod
    def detect_sql_injection(cls, text: str) -> bool:
        """
        Detect potential SQL injection attempts.
        
        Note: Always use parameterized queries/ORM.
        This is a supplementary check.
        """
        return bool(cls.SQL_INJECTION_PATTERN.search(text))
    
    @classmethod
    def detect_xss(cls, text: str) -> bool:
        """Detect potential XSS attempts."""
        return bool(cls.XSS_PATTERN.search(text))
    
    @classmethod
    def sanitize_input(cls, text: str, max_length: int = 10000) -> str:
        """
        Comprehensive input sanitization.
        
        Args:
            text: Input text to sanitize
            max_length: Maximum allowed length
        
        Returns:
            Sanitized text
        
        Raises:
            ValueError: If input contains suspicious patterns
        """
        if not text:
            return text
        
        # Truncate to max length
        text = text[:max_length]
        
        # Check for SQL injection
        if cls.detect_sql_injection(text):
            logger.warning(f"Potential SQL injection detected: {text[:100]}")
            raise ValueError("Input contains potentially malicious SQL patterns")
        
        # Check for XSS
        if cls.detect_xss(text):
            logger.warning(f"Potential XSS detected: {text[:100]}")
            raise ValueError("Input contains potentially malicious script patterns")
        
        # Remove HTML tags
        text = cls.remove_html_tags(text)
        
        return text


def setup_security_logging() -> None:
    """
    Configure logging to automatically redact PII.
    
    Note: This is a simple filter. For production, use a proper
    logging handler that redacts at the formatter level.
    """
    class PIIRedactionFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            # Redact PII from log message
            if isinstance(record.msg, str):
                record.msg = PIIRedactor.redact_all(record.msg)
            
            # Redact PII from log args
            if record.args:
                redacted_args = tuple(
                    PIIRedactor.redact_all(str(arg)) if isinstance(arg, str) else arg
                    for arg in record.args
                )
                record.args = redacted_args
            
            return True
    
    # Add filter to root logger
    logging.getLogger().addFilter(PIIRedactionFilter())
    logger.info("PII redaction filter installed on root logger")


# Export PII patterns for external use
PII_PATTERNS = {
    "email": PIIRedactor.EMAIL_PATTERN,
    "phone": PIIRedactor.PHONE_PATTERN,
    "credit_card": PIIRedactor.CREDIT_CARD_PATTERN,
    "ssn": PIIRedactor.SSN_PATTERN,
    "token": PIIRedactor.TOKEN_PATTERN,
}
