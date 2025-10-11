"""
FastAPI application entry point for Financial Advisor AI Backend.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import text

from app.api import auth_google, auth_hubspot, ingest, embeddings, chat, webhooks, health
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
    allow_origins=[settings.frontend_url] if settings.frontend_url else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure rate limiting
from app.core.rate_limiting import setup_rate_limiting
setup_rate_limiting(app)

# Configure Prometheus metrics
from app.core.observability import setup_metrics
setup_metrics(app)

# Mount API routers
app.include_router(health.router)  # Health checks first
app.include_router(auth_google.router, tags=["auth"])
app.include_router(auth_hubspot.router, tags=["auth"])
app.include_router(ingest.router)
app.include_router(embeddings.router)
app.include_router(chat.router)
app.include_router(webhooks.router)


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
