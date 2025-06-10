import secrets
import sqlite3
from fastapi import APIRouter, HTTPException, Request
import db
from models import URLRequest, URLResponse
from datetime import datetime, timezone
from urllib.parse import unquote
from fastapi.responses import JSONResponse

router = APIRouter()

def generate_unique_slug() -> str:
    """Generates a unique 4-byte hexadecimal slug."""
    with db.get_db_connection() as conn:
        while True:
            slug = secrets.token_hex(4)
            if not conn.execute("SELECT 1 FROM urls WHERE slug = ?", (slug,)).fetchone():
                return slug

def is_slug_available(slug: str) -> bool:
    """Checks if a slug is available for use."""
    with db.get_db_connection() as conn:
        return not conn.execute("SELECT 1 FROM urls WHERE slug = ?", (slug,)).fetchone()

@router.get("/api/analytics/{slug}")
async def get_url_analytics(slug: str) -> JSONResponse:
    """
    Get analytics for a shortened URL.
    Returns the click count for the given slug.
    """
    try:
        decoded_slug = unquote(slug)
        with db.get_db_connection() as conn:
            url_record = conn.execute(
                "SELECT clicks, created_at FROM urls WHERE slug = ?",
                (decoded_slug,)
            ).fetchone()
            
            if url_record is None:
                raise HTTPException(
                    status_code=404,
                    detail="URL not found"
                )
            
            return JSONResponse({
                "clicks": url_record["clicks"],
                "created_at": url_record["created_at"]
            })
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while getting URL analytics: {str(e)}"
        )

@router.post("/api/shorten", response_model=URLResponse)
async def create_short_url(
    url_request: URLRequest,
    request: Request
) -> URLResponse:
    """
    Creates a shortened URL for the given long URL.
    If a custom slug is provided, it will be used if available.
    Otherwise, a random slug will be generated.
    """
    long_url = str(url_request.long_url)
    
    if url_request.custom_slug:
        if not is_slug_available(url_request.custom_slug):
            raise HTTPException(
                status_code=409,
                detail="This custom slug is already taken"
            )
        slug = url_request.custom_slug
    else:
        slug = generate_unique_slug()
    
    created_time = datetime.now(timezone.utc)
    
    try:
        with db.get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO urls (slug, long_url, created_at)
                VALUES (?, ?, ?)
                """,
                (slug, long_url, created_time)
            )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="A URL with this slug already exists"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while creating the short URL: {str(e)}"
        )

    short_url = f"{request.base_url}{slug}"
    return URLResponse(
        short_url=short_url,
        clicks=0,
        created_at=created_time
    )

@router.delete("/api/urls/{slug:path}", status_code=204, include_in_schema=False)
async def delete_url(slug: str):
    """Deletes a shortened URL."""
    try:
        decoded_slug = unquote(slug)
        with db.get_db_connection() as conn:
            # Check if the URL exists before deleting
            existing_url = conn.execute("SELECT 1 FROM urls WHERE slug = ?", (decoded_slug,)).fetchone()
            if not existing_url:
                raise HTTPException(status_code=404, detail="URL not found")
            
            conn.execute("DELETE FROM urls WHERE slug = ?", (decoded_slug,))
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while deleting the URL: {str(e)}"
        )
