import secrets
import sqlite3
from fastapi import APIRouter, HTTPException
import db
from models import URLRequest, URLResponse
from datetime import datetime, timezone
from urllib.parse import unquote
from fastapi.responses import JSONResponse
import logging
from typing import Set
import threading
from routers.redirect import invalidate_cache

# Reserved words that cannot be used as custom slugs
RESERVED_SLUGS = {
    "api", "static", "favicon.ico", "apple-touch-icon.png", 
    "apple-touch-icon-precomposed.png", "admin", "root", "www",
    "mail", "ftp", "localhost", "dashboard", "settings", "help",
    "about", "contact", "privacy", "terms", "robots.txt", "sitemap.xml"
}

router = APIRouter()
logger = logging.getLogger(__name__)

# Pre-generated slug pool for better performance with thread safety
slug_pool: Set[str] = set()
POOL_SIZE = 1000
MAX_GENERATION_ATTEMPTS = 100
slug_pool_lock = threading.Lock()



def refill_slug_pool() -> None:
    """Refill the slug pool with pre-generated unique slugs."""
    global slug_pool
    with slug_pool_lock:
        with db.get_db_connection() as conn:
            while len(slug_pool) < POOL_SIZE:
                candidate = secrets.token_hex(4)
                if not conn.execute("SELECT 1 FROM urls WHERE slug = ? LIMIT 1", (candidate,)).fetchone():
                    slug_pool.add(candidate)

def get_unique_slug_from_pool() -> str:
    """Get a unique slug from the pre-generated pool."""
    with slug_pool_lock:
        if not slug_pool:
            refill_slug_pool()
        
        if slug_pool:
            return slug_pool.pop()
    
    # Fallback to direct generation if pool is empty
    return generate_unique_slug_fallback()

def generate_unique_slug_fallback() -> str:
    """Fallback method for slug generation with attempt limit."""
    with db.get_db_connection() as conn:
        for _ in range(MAX_GENERATION_ATTEMPTS):
            slug = secrets.token_hex(4)
            if not conn.execute("SELECT 1 FROM urls WHERE slug = ? LIMIT 1", (slug,)).fetchone():
                return slug
        
        # If we can't find a unique slug after max attempts, increase length
        for _ in range(MAX_GENERATION_ATTEMPTS):
            slug = secrets.token_hex(6)  # Longer slug
            if not conn.execute("SELECT 1 FROM urls WHERE slug = ? LIMIT 1", (slug,)).fetchone():
                return slug
        
        raise HTTPException(
            status_code=500,
            detail="Unable to generate unique slug after multiple attempts"
        )

def is_slug_available(slug: str) -> bool:
    """Checks if a slug is available for use."""
    with db.get_db_connection() as conn:
        return not conn.execute("SELECT 1 FROM urls WHERE slug = ? LIMIT 1", (slug,)).fetchone()

@router.get("/api/analytics/{slug:path}")
async def get_url_analytics(slug: str) -> JSONResponse:
    """
    Get analytics for a shortened URL.
    Returns the click count for the given slug.
    """
    try:
        decoded_slug = unquote(slug)
        with db.get_db_connection() as conn:
            url_record = conn.execute(
                "SELECT clicks, created_at FROM urls WHERE slug = ? LIMIT 1",
                (decoded_slug,)
            ).fetchone()
            
            if url_record is None:
                logger.warning(f"Analytics requested for non-existent slug: {decoded_slug}")
                raise HTTPException(
                    status_code=404,
                    detail="URL not found"
                )
            
            return JSONResponse({
                "clicks": url_record["clicks"],
                "created_at": url_record["created_at"]
            })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analytics for slug {slug}: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while getting URL analytics"
        )

@router.post("/api/shorten", response_model=URLResponse)
async def create_short_url(
    url_request: URLRequest
) -> URLResponse:
    """
    Creates a shortened URL slug for the given long URL.
    If a custom slug is provided, it will be used if available.
    Otherwise, a random slug will be generated.
    Returns only the slug, not the full URL.
    """
    long_url = str(url_request.long_url)
    created_time = datetime.now(timezone.utc)
    
    # Generate slug with atomic database operations
    if url_request.custom_slug:
        slug = url_request.custom_slug.lower().strip()
        
        # Validate against reserved words
        if slug in RESERVED_SLUGS or slug.startswith("api/"):
            raise HTTPException(
                status_code=400,
                detail="This slug is reserved and cannot be used"
            )
        # Use INSERT OR IGNORE to handle race conditions atomically
        try:
            with db.get_db_connection() as conn:
                # Try to insert directly - will fail if slug exists
                result = conn.execute(
                    "INSERT OR IGNORE INTO urls (slug, long_url, created_at) VALUES (?, ?, ?)",
                    (slug, long_url, created_time)
                )
                if result.rowcount == 0:
                    # Slug already exists
                    raise HTTPException(
                        status_code=409,
                        detail="This custom slug is already taken"
                    )
                logger.info(f"Created short URL: {slug} -> {long_url}")
                return URLResponse(
                    short_url=slug,
                    long_url=long_url,
                    clicks=0,
                    created_at=created_time
                )
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=409,
                detail="This custom slug is already taken"
            )
        except Exception as e:
            logger.error(f"Error creating short URL for {long_url}: {e}")
            raise HTTPException(
                status_code=500,
                detail="An error occurred while creating the short URL"
            )
    else:
        # For auto-generated slugs, use atomic insert with retry logic
        for _ in range(MAX_GENERATION_ATTEMPTS):
            slug = get_unique_slug_from_pool()
            try:
                with db.get_db_connection() as conn:
                    conn.execute(
                        "INSERT INTO urls (slug, long_url, created_at) VALUES (?, ?, ?)",
                        (slug, long_url, created_time)
                    )
                    logger.info(f"Created short URL: {slug} -> {long_url}")
                    return URLResponse(
                        short_url=slug,
                        long_url=long_url,
                        clicks=0,
                        created_at=created_time
                    )
            except sqlite3.IntegrityError:
                # Slug collision, try again
                continue
            except Exception as e:
                logger.error(f"Error creating short URL for {long_url}: {e}")
                raise HTTPException(
                    status_code=500,
                    detail="An error occurred while creating the short URL"
                )
        
        # If we get here, we couldn't generate a unique slug
        raise HTTPException(
            status_code=500,
            detail="Unable to generate a unique slug after multiple attempts"
        )

@router.delete("/api/urls/{slug:path}", status_code=204, include_in_schema=False)
async def delete_url(slug: str):
    """Deletes a shortened URL."""
    try:
        decoded_slug = unquote(slug)
        with db.get_db_connection() as conn:
            # Check if the URL exists before deleting
            existing_url = conn.execute(
                "SELECT 1 FROM urls WHERE slug = ? LIMIT 1", 
                (decoded_slug,)
            ).fetchone()
            if not existing_url:
                logger.warning(f"Delete attempted for non-existent slug: {decoded_slug}")
                raise HTTPException(status_code=404, detail="URL not found")
            
            conn.execute("DELETE FROM urls WHERE slug = ?", (decoded_slug,))
            # Invalidate cache after successful deletion
            invalidate_cache(decoded_slug)
            logger.info(f"Deleted URL with slug: {decoded_slug}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting URL with slug {slug}: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while deleting the URL"
        )

# Initialize slug pool on startup
def init_slug_pool() -> None:
    """Initialize the slug pool on application startup."""
    try:
        refill_slug_pool()
        logger.info(f"Initialized slug pool with {len(slug_pool)} slugs")
    except Exception as e:
        logger.error(f"Failed to initialize slug pool: {e}")

# Initialize slug pool after all function definitions
init_slug_pool()
