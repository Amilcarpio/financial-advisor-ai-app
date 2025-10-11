"""HubSpot authentication endpoints."""
from fastapi import APIRouter

router = APIRouter(prefix="/auth/hubspot", tags=["hubspot-auth"])


@router.get("/health")
async def hubspot_auth_health() -> dict[str, str]:
    return {"status": "ok"}
