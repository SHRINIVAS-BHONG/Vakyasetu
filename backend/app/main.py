import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.endpoints import router as api_v1_router, health_check
from app.services.cache import get_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup and graceful shutdown lifecycle."""
    logger.info(f"Starting {settings.PROJECT_NAME} application...")
    # Initialize cache connection pool eagerly
    cache = get_cache()
    logger.info(f"Cache engine initialized at {cache.db_path}")
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME} application...")
    cache.close()
    logger.info("Cache connections closed cleanly.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Production Computational Sanskrit NLP & Pedagogical Translation Engine for CBSE/NCERT Classes 6–10. "
        "Provides end-to-end sandhi splitting, grammatical morphological cards, and natural English translations."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Configure CORS Middleware for Frontend Clients (React, Vite, Streamlit)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_v1_router, prefix=settings.API_V1_STR)

@app.get(
    "/",
    summary="Root Service Status",
    description="Returns service metadata, version, and interactive API documentation links.",
)
async def root():
    return {
        "project": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "online",
        "documentation": "/docs",
        "api_v1_prefix": settings.API_V1_STR,
    }

@app.get(
    "/health",
    summary="Root Liveness Probe",
    description="Standard container / Kubernetes readiness and liveness probe.",
)
async def root_health():
    return await health_check()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
