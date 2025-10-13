"""
FastAPI application entry point for Financial Advisor AI Backend.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import auth_google, auth_hubspot, ingest, embeddings, chat, webhooks, health, rules, verification
from app.core.config import settings
from app.core.database import engine, create_db_and_tables
from app.core.security import SecurityHeadersMiddleware, setup_security_logging
from app.core.logging_config import CorrelationIdMiddleware, setup_structured_logging

# Configure structured logging
setup_structured_logging(log_level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Security check: Validate SECRET_KEY
    if settings.secret_key == "dev-secret-key-change-in-production-min-32-characters":
        if settings.app_env == "production":
            logger.error("CRITICAL: Default SECRET_KEY detected in production!")
            raise ValueError("Must set custom SECRET_KEY in production")
        logger.warning("WARNING: Using default SECRET_KEY - DO NOT use in production!")
    
    if len(settings.secret_key) < 32:
        raise ValueError("SECRET_KEY must be at least 32 characters long")
    
    # Startup: Create database tables and pgvector extension
    create_db_and_tables()
    
    # Setup security logging with PII redaction
    setup_security_logging()
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown: cleanup if needed
    engine.dispose()
    logger.info("Application shutdown complete")


# Initialize FastAPI application
app = FastAPI(
    title="Financial Advisor AI Backend",
    description="AI-powered assistant for financial advisors with email/CRM integration and RAG",
    version="1.0.0",
    lifespan=lifespan,
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add correlation ID middleware for request tracking
app.add_middleware(CorrelationIdMiddleware)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://amilcarpio.github.io", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Correlation-ID", "X-Requested-With"],
    expose_headers=["X-Correlation-ID"],
    max_age=600,
)

# Configure rate limiting
from app.core.rate_limiting import setup_rate_limiting
setup_rate_limiting(app)

# Configure Prometheus metrics
from app.core.observability import setup_metrics
setup_metrics(app)

# Mount API routers
app.include_router(health.router)  # Health checks first
app.include_router(verification.router)  # Domain verification (no prefix - root level)
app.include_router(auth_google.auth_router, prefix="/api", tags=["auth"])
app.include_router(auth_google.router, prefix="/api", tags=["auth"])
app.include_router(auth_hubspot.router, prefix="/api", tags=["auth"])
app.include_router(ingest.router, prefix="/api")
app.include_router(embeddings.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")
app.include_router(rules.router)  # Memory Rules API


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint with API information.
    """
    return {
        "message": "Financial Advisor AI Backend API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "metrics": "/metrics"
    }
