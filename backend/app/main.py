"""
FastAPI application entry point for Financial Advisor AI Backend.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import text

from app.api import auth_google, auth_hubspot
from app.core.config import settings
from app.core.database import engine, create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup: Create database tables and pgvector extension
    create_db_and_tables()
    
    yield
    
    # Shutdown: cleanup if needed
    engine.dispose()


# Initialize FastAPI application
app = FastAPI(
    title="Financial Advisor AI Backend",
    description="AI-powered assistant for financial advisors with email/CRM integration and RAG",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url] if settings.frontend_url else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(auth_google.router, tags=["auth"])
app.include_router(auth_hubspot.router, tags=["auth"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.
    Returns 200 if the application and database are healthy.
    """
    try:
        # Test database connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
        }


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint.
    """
    return {
        "message": "Financial Advisor AI Backend API",
        "docs": "/docs",
        "health": "/health",
    }
