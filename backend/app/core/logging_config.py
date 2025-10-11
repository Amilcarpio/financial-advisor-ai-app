"""
Structured JSON logging configuration.

Provides:
- JSON formatted logs for easy parsing
- Correlation IDs for request tracking
- Contextual information in all logs
"""

import json
import logging
import sys
import traceback
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class JSONFormatter(logging.Formatter):
    """
    Format log records as JSON for structured logging.
    
    Each log entry includes:
    - timestamp (ISO 8601)
    - level
    - message
    - logger name
    - correlation_id (if available)
    - extra fields
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add correlation ID if available
        if hasattr(record, 'correlation_id'):
            log_entry["correlation_id"] = record.correlation_id  # type: ignore
        
        # Add user ID if available
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id  # type: ignore
        
        # Add request ID if available
        if hasattr(record, 'request_id'):
            log_entry["request_id"] = record.request_id  # type: ignore
        
        # Add function/module info
        log_entry["function"] = record.funcName
        log_entry["module"] = record.module
        log_entry["line"] = record.lineno
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Add any extra fields
        extra_fields = {
            k: v for k, v in record.__dict__.items()
            if k not in [
                'name', 'msg', 'args', 'created', 'filename', 'funcName',
                'levelname', 'levelno', 'lineno', 'module', 'msecs',
                'message', 'pathname', 'process', 'processName', 'relativeCreated',
                'thread', 'threadName', 'exc_info', 'exc_text', 'stack_info',
                'correlation_id', 'user_id', 'request_id'
            ]
        }
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        return json.dumps(log_entry)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs to requests.
    
    Generates a unique correlation ID for each request and adds it
    to the request state. This ID is then included in all logs
    for that request, making it easy to trace a request through
    the system.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Any) -> Any:
        # Generate correlation ID
        correlation_id = str(uuid4())
        
        # Add to request state
        request.state.correlation_id = correlation_id
        
        # Add response header
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response


def setup_structured_logging(log_level: str = "INFO") -> None:
    """
    Configure structured JSON logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Create JSON formatter
    formatter = JSONFormatter()
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add JSON handler to stdout
    json_handler = logging.StreamHandler(sys.stdout)
    json_handler.setFormatter(formatter)
    root_logger.addHandler(json_handler)
    
    # Silence noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    logging.info("Structured JSON logging configured")


def get_logger_with_context(
    name: str,
    correlation_id: Optional[str] = None,
    user_id: Optional[int] = None,
    request_id: Optional[str] = None
) -> logging.LoggerAdapter:
    """
    Get a logger with contextual information.
    
    Args:
        name: Logger name
        correlation_id: Correlation ID for request tracking
        user_id: User ID for user-specific logs
        request_id: Request ID
    
    Returns:
        LoggerAdapter with context
    """
    logger = logging.getLogger(name)
    
    extra = {}
    if correlation_id:
        extra["correlation_id"] = correlation_id
    if user_id:
        extra["user_id"] = user_id
    if request_id:
        extra["request_id"] = request_id
    
    return logging.LoggerAdapter(logger, extra)


# Example usage:
# logger = get_logger_with_context(__name__, correlation_id=request.state.correlation_id)
# logger.info("Processing request", extra={"user_email": user.email})
