"""Data ingestion endpoints."""
from fastapi import APIRouter

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("/queue")
async def queue_ingest() -> dict[str, str]:
    return {"status": "queued"}
