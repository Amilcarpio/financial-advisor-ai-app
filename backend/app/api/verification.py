"""
Static file serving for domain verification.

Handles verification files from:
- Google Search Console (for Calendar webhook verification)
- Other services as needed
"""
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from ..core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["verification"])

# Path to static files directory
STATIC_DIR = Path(__file__).parent.parent / "static"


@router.get("/google{code}.html")
async def google_site_verification(code: str):
    """
    Serve Google Search Console verification file.
    
    Google expects a file named: google[CODE].html
    Example: google123abc456def.html
    
    This endpoint looks for the file in app/static/ directory.
    If the file exists, it serves it. If not, returns 404.
    
    Setup:
    1. Go to https://search.google.com/search-console/welcome
    2. Add property: https://financial-advisor-ai-app.fly.dev
    3. Choose "HTML file" verification method
    4. Google will provide a file like: google44732a03c4f9cf42.html
    5. The file should already be in app/static/
    6. Click "Verify" in Google Search Console
    
    Args:
        code: The verification code from Google (extracted from URL path)
        
    Returns:
        HTML file content for verification
    """
    filename = f"google{code}.html"
    file_path = STATIC_DIR / filename
    
    if not file_path.exists():
        logger.warning(f"Google verification file not found: {filename}")
        raise HTTPException(status_code=404, detail="Verification file not found")
    
    logger.info(f"Serving Google verification file: {filename}")
    
    # Return the file content as plain text (Google expects plain text, not HTML)
    return FileResponse(
        path=str(file_path),
        media_type="text/html",
        filename=filename
    )


@router.get("/googlehostedservice.html", response_class=PlainTextResponse)
async def google_hosted_service() -> str:
    """
    Alternative Google verification endpoint.
    
    Some Google services use this alternative verification file.
    """
    return "google-site-verification: googlehostedservice.html"
