"""Tooling endpoints for agent actions."""
from fastapi import APIRouter

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/health")
async def tools_health() -> dict[str, str]:
    return {"status": "ok"}
