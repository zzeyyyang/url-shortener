import sqlite3
from contextlib import contextmanager
from typing import Generator

DATABASE_FILE = "urls.db"

@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    """Returns a connection to the SQLite database with proper error handling."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_FILE, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        # It's better to raise a custom exception type here.
        raise Exception(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

def init_db() -> None:
    """Initializes the database and creates the 'urls' table if it doesn't exist."""
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                long_url TEXT NOT NULL,
                clicks INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

# NOTE: Calling init_db() here is convenient for simple applications.
# For more complex applications, it's better to manage database
# initialization explicitly, for example, in an application startup event.
init_db()
