from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "VākyaSetu"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # SQLite Cache configuration
    CACHE_DB_PATH: str = "vakyasetu_cache.db"
    
    # Model & Computational NLP configurations
    DEVICE: str = "cpu"
    INDIC_TRANS_MODEL_PATH: str = "ml/checkpoints/indictrans2"
    MAX_SANDHI_PATHS: int = 5
    DEFAULT_CONFIDENCE_THRESHOLD: float = 0.5
    
    # CORS Origins for Mayank's frontend (Streamlit & React)
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8501",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8501",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
