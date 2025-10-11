"""Google authentication endpoints."""
from fastapi import APIRouter

router = APIRouter(prefix="/auth/google", tags=["google-auth"])


@router.get("/health")
async def google_auth_health() -> dict[str, str]:
    """Lightweight endpoint to verify router wiring."""

    return {"status": "ok"}
