"""API routers aggregation."""
from fastapi import APIRouter

from . import auth_google, auth_hubspot, chat, ingest, tools, webhooks

api_router = APIRouter()
api_router.include_router(auth_google.router)
api_router.include_router(auth_hubspot.router)
api_router.include_router(ingest.router)
api_router.include_router(chat.router)
api_router.include_router(tools.router)
api_router.include_router(webhooks.router)

__all__ = ["api_router"]
