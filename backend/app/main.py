"""FastAPI application entrypoint."""
from fastapi import FastAPI

from .api import api_router
from .core.config import settings
from .core.database import create_db_and_tables

app = FastAPI(title=settings.app_name)
app.include_router(api_router, prefix="/api")


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize database state when the application boots."""

    create_db_and_tables()


@app.get("/")
async def health() -> dict[str, str]:
    """Simple health check endpoint."""

    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
    }
