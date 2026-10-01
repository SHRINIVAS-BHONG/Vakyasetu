import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.endpoints import router as api_v1_router, health_check
from app.services.cache import get_cache
from app.services.orchestrator import get_orchestrator_service

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application startup, cache pre-warming, and graceful shutdown lifecycle."""
    logger.info(f"Starting {settings.PROJECT_NAME} application...")
    # 1. Initialize cache connection eagerly
    cache = get_cache()
    logger.info(f"Cache engine initialized at {cache.db_path}")

    # 2. Pre-warm linguistic pipeline and caches to eliminate first-request latency
    orchestrator = get_orchestrator_service()
    seed_sentences = [
        "बालकः पुस्तकं पठति।",
        "वयं विद्यालये पठामः।",
        "सः सदा सत्यं वदति।",
    ]
    for seed in seed_sentences:
        try:
            orchestrator.analyze(seed)
        except Exception as e:
            logger.debug(f"Pre-warming seed '{seed}' skipped: {e}")
    logger.info("Linguistic pipeline and memory caches pre-warmed successfully.")

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

# Configure GZip Compression Middleware (compresses responses > 1KB)
app.add_middleware(GZipMiddleware, minimum_size=1000)

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
