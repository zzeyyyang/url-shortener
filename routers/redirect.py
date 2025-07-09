from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, Response
from typing import Union, List
import db
from urllib.parse import unquote
import logging
from models import URLResponse
from typing import Dict, Optional

router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Simple in-memory cache for frequently accessed URLs
url_cache: Dict[str, Optional[str]] = {}
MAX_CACHE_SIZE = 1000

def get_cached_url(slug: str) -> Optional[str]:
    """Get URL from cache if available."""
    return url_cache.get(slug)

def cache_url(slug: str, url: str) -> None:
    """Cache URL with basic size limit."""
    if len(url_cache) >= MAX_CACHE_SIZE:
        # Remove oldest entry (simple FIFO)
        oldest_key = next(iter(url_cache))
        del url_cache[oldest_key]
    url_cache[slug] = url

def invalidate_cache(slug: str) -> None:
    """Remove a URL from the cache."""
    if slug in url_cache:
        del url_cache[slug]

@router.get("/api/urls", response_model=List[URLResponse])
async def get_all_urls():
    """Get all shortened URLs."""
    try:
        with db.get_db_connection() as conn:
            records = conn.execute("SELECT slug, long_url, clicks, created_at FROM urls ORDER BY created_at DESC").fetchall()
            
            
            urls = [
                URLResponse(
                    short_url=rec["slug"],
                    long_url=rec["long_url"],
                    clicks=rec["clicks"],
                    created_at=rec["created_at"]
                ) for rec in records
            ]
            return urls
    except Exception as e:
        logger.error(f"Error getting all URLs: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while getting all URLs: {str(e)}"
        )

@router.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return transparent favicon to prevent browser from showing any icon."""
    # Return a transparent 1x1 PNG pixel
    transparent_png = bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c626001000000050001d44d1eb40000000049454e44ae426082')
    return Response(content=transparent_png, media_type="image/png")

@router.get("/apple-touch-icon.png", include_in_schema=False)
async def apple_touch_icon():
    """Return transparent PNG for Apple touch icon."""
    # Return a transparent 1x1 PNG pixel
    transparent_png = bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c626001000000050001d44d1eb40000000049454e44ae426082')
    return Response(content=transparent_png, media_type="image/png")

@router.get("/apple-touch-icon-precomposed.png", include_in_schema=False)
async def apple_touch_icon_precomposed():
    """Return transparent PNG for Apple touch icon precomposed."""
    # Return a transparent 1x1 PNG pixel
    transparent_png = bytes.fromhex('89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c626001000000050001d44d1eb40000000049454e44ae426082')
    return Response(content=transparent_png, media_type="image/png")

@router.get("/{slug:path}", response_model=None, include_in_schema=False)
async def redirect_to_long_url(slug: str) -> Union[RedirectResponse, HTMLResponse]:
    """
    Redirects to the long URL associated with the given slug and increments the click count.
    Implements caching and security headers.
    """
    try:
        decoded_slug = unquote(slug)
        
        # Check cache first
        cached_url = get_cached_url(decoded_slug)
        if cached_url:
            # Still need to increment clicks in database
            with db.get_db_connection() as conn:
                conn.execute(
                    "UPDATE urls SET clicks = clicks + 1 WHERE slug = ?",
                    (decoded_slug,)
                )
            
            headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
            
            return RedirectResponse(
                url=cached_url,
                status_code=307,
                headers=headers
            )
        
        with db.get_db_connection() as conn:
            # Single transaction: get URL and increment clicks atomically
            url_record = conn.execute(
                "SELECT long_url FROM urls WHERE slug = ?",
                (decoded_slug,)
            ).fetchone()
            
            if url_record is None:
                logger.info(f"URL not found for slug: {decoded_slug}")
                return HTMLResponse(
                    content="""
                    <html>
                        <head>
                            <title>URL Not Found</title>
                        </head>
                        <body>
                            <h1>URL Not Found</h1>
                            <p>The shortened URL you're looking for doesn't exist.</p>
                            <p><a href="/">Create a new shortened URL</a></p>
                        </body>
                    </html>
                    """,
                    status_code=404
                )
            
            # Cache the URL for future requests
            cache_url(decoded_slug, url_record["long_url"])
            
            # Increment the click count in same transaction
            conn.execute(
                "UPDATE urls SET clicks = clicks + 1 WHERE slug = ?",
                (decoded_slug,)
            )
            
            # Set security and no-caching headers
            headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
                "X-XSS-Protection": "1; mode=block",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
            
            return RedirectResponse(
                url=url_record["long_url"],
                status_code=307,  # Use 307 for a temporary redirect
                headers=headers
            )
            
    except Exception as e:
        logger.error(f"Error processing redirect for slug {slug}: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing the redirect"
        )
