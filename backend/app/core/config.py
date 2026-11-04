from typing import Optional, Any
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "VākyaSetu"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # SQLite Cache configuration
    CACHE_DB_PATH: str = str(Path(__file__).resolve().parents[2] / "vakyasetu_cache.db")
    
    # Model & Computational NLP configurations
    DEVICE: str = "cpu"
    INDIC_TRANS_MODEL_PATH: str = "ml/checkpoints/indictrans2"
    MAX_SANDHI_PATHS: int = 5
    DEFAULT_CONFIDENCE_THRESHOLD: float = 0.5
    
    # CORS Origins for Frontend Clients (Localhost, Render, Custom domains)
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8501",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8501",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            if v.strip() == "*":
                return ["*"]
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # Render Keep-Alive / Self-Ping configuration (prevents idle spin-down)
    ENABLE_SELF_PING: bool = True
    SELF_PING_INTERVAL_SECONDS: int = 480  # 8 minutes
    RENDER_EXTERNAL_URL: Optional[str] = None
    SELF_PING_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
