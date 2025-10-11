"""
Health check endpoints for monitoring and load balancers.

Provides:
- /health: Basic health check
- /ready: Readiness check (dependencies OK)
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlmodel import text, Session

from app.core.database import engine

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns 200 if the application is running.
    Used by load balancers and monitoring systems.
    
    This endpoint should be lightweight and always succeed
    unless the application is completely broken.
    """
    return {
        "status": "healthy",
        "service": "financial-advisor-ai-backend",
        "version": "1.0.0"
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> Any:
    """
    Readiness check endpoint.
    
    Returns 200 if the application is ready to accept traffic.
    Checks:
    - Database connectivity
    - (Optional) External service dependencies
    
    Used by Kubernetes, Fly.io, and other orchestrators
    to determine when to route traffic to this instance.
    """
    checks: Dict[str, Any] = {
        "database": "unknown",
        "overall": "unknown"
    }
    
    # Check database connectivity
    try:
        with Session(engine) as db:
            result = db.execute(text("SELECT 1")).fetchone()  # type: ignore
            if result:
                checks["database"] = "healthy"
            else:
                checks["database"] = "unhealthy"
                logger.error("Database readiness check failed: no result")
    except Exception as e:
        checks["database"] = "unhealthy"
        logger.error(f"Database readiness check failed: {e}")
    
    # Determine overall status
    if checks["database"] == "healthy":
        checks["overall"] = "ready"
        return checks
    else:
        checks["overall"] = "not ready"
        # Return 503 Service Unavailable
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=checks
        )


@router.get("/health/database")
async def database_health() -> Dict[str, Any]:
    """
    Detailed database health check.
    
    Returns information about:
    - Connection status
    - Active connections
    - Database version
    """
    health_info = {
        "status": "unknown",
        "connection": "unknown",
        "version": "unknown"
    }
    
    try:
        with Session(engine) as db:
            # Test connection
            result = db.execute(text("SELECT 1")).fetchone()  # type: ignore
            health_info["connection"] = "connected" if result else "disconnected"
            
            # Get PostgreSQL version
            version_result = db.execute(text("SELECT version()")).fetchone()  # type: ignore
            if version_result:
                health_info["version"] = str(version_result[0])
            
            # Get active connections count (if we have permissions)
            try:
                conn_result = db.execute(  # type: ignore
                    text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
                ).fetchone()
                if conn_result:
                    health_info["active_connections"] = str(conn_result[0])
            except Exception as e:
                logger.debug(f"Could not get connection count: {e}")
            
            health_info["status"] = "healthy"
    except Exception as e:
        health_info["status"] = "unhealthy"
        health_info["error"] = str(e)
        logger.error(f"Database health check failed: {e}")
    
    return health_info

