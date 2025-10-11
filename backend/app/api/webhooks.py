"""Webhook handlers."""
from fastapi import APIRouter

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/receive")
async def receive_webhook() -> dict[str, str]:
    return {"status": "accepted"}
