from fastapi import APIRouter, HTTPException, Response, Request
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from typing import Union, List
import db
from datetime import datetime, timedelta, timezone
from urllib.parse import unquote
import logging
from models import URLResponse
from config import config

router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.get("/api/urls", response_model=List[URLResponse])
async def get_all_urls():
    """Get all shortened URLs."""
    try:
        with db.get_db_connection() as conn:
            records = conn.execute("SELECT slug, long_url, clicks, created_at FROM urls ORDER BY created_at DESC").fetchall()
            
            # Manually construct the short_url for each record
            base_url = f"{config.BASE_URL}/"
            
            urls = [
                URLResponse(
                    short_url=f"{base_url}{rec['slug']}",
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

@router.get("/{slug}/stats")
async def get_url_stats(slug: str) -> JSONResponse:
    """Get the current stats for a shortened URL."""
    try:
        decoded_slug = unquote(slug)
        with db.get_db_connection() as conn:
            url_record = conn.execute(
                "SELECT clicks FROM urls WHERE slug = ?",
                (decoded_slug,)
            ).fetchone()
            
            if url_record is None:
                raise HTTPException(
                    status_code=404,
                    detail="URL not found"
                )
            
            return JSONResponse({
                "clicks": url_record["clicks"]
            })
    except Exception as e:
        logger.error(f"Error getting URL stats for slug {slug}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while getting URL stats: {str(e)}"
        )

@router.get("/{slug:path}", response_model=None, include_in_schema=False)
async def redirect_to_long_url(slug: str, request: Request, response: Response) -> Union[RedirectResponse, HTMLResponse]:
    """
    Redirects to the long URL associated with the given slug and increments the click count.
    Implements caching and security headers.
    """
    try:
        decoded_slug = unquote(slug)
        
        with db.get_db_connection() as conn:
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
            
            # Increment the click count
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
            detail=f"An error occurred while processing the redirect: {str(e)}"
        )
