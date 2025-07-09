import os

class Config:
    """Application configuration with environment variable support."""
    
    # Server configuration
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    BASE_URL: str = os.getenv("BASE_URL", f"http://{HOST}:{PORT}")
    
    # Database configuration
    DATABASE_FILE: str = os.getenv("DATABASE_FILE", "urls.db")
    DATABASE_TIMEOUT: int = int(os.getenv("DATABASE_TIMEOUT", "5"))
    
    # Application settings
    RELOAD: bool = os.getenv("RELOAD", "true").lower() == "true"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # URL shortening settings
    SLUG_LENGTH: int = int(os.getenv("SLUG_LENGTH", "4"))
    MAX_CUSTOM_SLUG_LENGTH: int = int(os.getenv("MAX_CUSTOM_SLUG_LENGTH", "32"))
    
    @classmethod
    def load_from_env(cls) -> None:
        """Load configuration from .env file if it exists."""
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

# Create global config instance
config = Config()