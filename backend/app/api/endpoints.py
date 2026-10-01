import asyncio
import logging
import sys
import time
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Query, status

from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    BatchAnalyzeRequest,
    BatchAnalyzeResponse,
    VakyaSetuResponse,
    MorphologyRequest,
    WordAnalysis,
    HealthStatus,
)
from app.services.cache import get_cache
from app.services.morphology import get_morphology_service
from app.services.orchestrator import get_orchestrator_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Master Sanskrit Linguistic Analysis Endpoint",
    description="Processes raw Sanskrit prose through the complete pipeline with async worker thread offloading.",
)
async def analyze_sentence(
    request: AnalyzeRequest,
    bypass_cache: bool = Query(False, description="Set to true to force full re-computation and bypass cache"),
) -> AnalyzeResponse:
    """Master endpoint executing end-to-end analysis offloaded to async threadpool."""
    if not request.text or not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input text cannot be empty or solely whitespace.",
        )
    try:
        orchestrator = get_orchestrator_service()
        response = await asyncio.to_thread(
            orchestrator.analyze,
            request.text,
            bypass_cache=bypass_cache,
        )
        return response
    except Exception as e:
        logger.error(f"Error executing analysis for '{request.text}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Linguistic pipeline execution failed: {str(e)}",
        )

@router.post(
    "/analyze/batch",
    response_model=BatchAnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Concurrent Batch Linguistic Analysis Endpoint",
    description="Concurrently analyzes multiple Sanskrit sentences across the worker pool using asyncio.gather.",
)
async def analyze_batch(
    request: BatchAnalyzeRequest,
    bypass_cache: bool = Query(False, description="Set to true to force full re-computation and bypass cache"),
) -> BatchAnalyzeResponse:
    """Processes multiple sentences concurrently with high throughput."""
    if not request.sentences:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sentences list cannot be empty.",
        )
    try:
        orchestrator = get_orchestrator_service()
        t0 = time.perf_counter()
        tasks = [
            asyncio.to_thread(orchestrator.analyze, s, bypass_cache=bypass_cache)
            for s in request.sentences
        ]
        results = await asyncio.gather(*tasks)
        total_time_ms = round((time.perf_counter() - t0) * 1000, 2)
        return BatchAnalyzeResponse(
            results=list(results),
            total_sentences=len(results),
            total_processing_time_ms=total_time_ms,
        )
    except Exception as e:
        logger.error(f"Error executing batch analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch execution failed: {str(e)}",
        )

@router.post(
    "/morphology",
    response_model=List[WordAnalysis],
    status_code=status.HTTP_200_OK,
    summary="Granular Word-Level Morphology Endpoint",
    description="Analyzes specific Sanskrit word tokens offloaded to async threadpool.",
)
async def analyze_morphology(request: MorphologyRequest) -> List[WordAnalysis]:
    """Token inspection endpoint for student chips and interactive grammar cards."""
    if not request.tokens:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tokens list cannot be empty.",
        )
    try:
        morphology_service = get_morphology_service()
        results = await asyncio.to_thread(
            morphology_service.analyze_tokens,
            request.tokens,
        )
        return results
    except Exception as e:
        logger.error(f"Error analyzing tokens {request.tokens}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Morphological analysis failed: {str(e)}",
        )

@router.get(
    "/health",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
    summary="System Health & Readiness Check",
    description="Provides liveness, runtime environment, cache database connectivity, and internal service status.",
)
async def health_check() -> HealthStatus:
    """Liveness probe verifying database connectivity and service availability."""
    cache = get_cache()
    cache_ok = False
    try:
        stats = cache.get_stats()
        cache_ok = "error" not in stats
    except Exception:
        cache_ok = False

    return HealthStatus(
        status="healthy" if cache_ok else "degraded",
        version="1.0.0",
        python_version=sys.version.split()[0],
        cache_connected=cache_ok,
        services={
            "cache": "connected" if cache_ok else "disconnected",
            "normalizer": "available",
            "sandhi": "available",
            "morphology": "available",
            "translation": "available",
            "orchestrator": "available",
        },
    )

@router.get(
    "/cache/stats",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Cache Telemetry & Hit Ratio",
    description="Returns detailed telemetry for the hybrid L1 in-memory and L2 SQLite cache.",
)
async def cache_statistics() -> Dict[str, Any]:
    """Returns granular hit, miss, and capacity metrics for monitoring."""
    cache = get_cache()
    return cache.get_stats()

@router.post(
    "/cache/clear",
    status_code=status.HTTP_200_OK,
    summary="Purge Cache Database",
    description="Empties both L1 in-memory LRU and L2 persistent SQLite cache tables.",
)
async def clear_cache() -> Dict[str, str]:
    """Admin utility to flush cache during development or testing."""
    cache = get_cache()
    await asyncio.to_thread(cache.clear)
    return {"message": "Cache successfully cleared."}

