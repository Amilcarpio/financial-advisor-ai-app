"""Chat interaction endpoints."""
from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/messages")
async def chat_message() -> dict[str, str]:
    return {"status": "received"}
