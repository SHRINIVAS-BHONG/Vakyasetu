import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.cache import get_cache

@pytest.fixture(scope="module")
def client():
    """Provides a TestClient for FastAPI endpoints with clean cache state."""
    cache = get_cache()
    cache.clear()
    with TestClient(app) as test_client:
        yield test_client
    cache.clear()

def test_root_endpoint(client):
    """Verify that root endpoint returns service metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "VākyaSetu"
    assert data["status"] == "online"
    assert data["documentation"] == "/docs"

def test_root_health_endpoint(client):
    """Verify that /health root probe reports healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data
    assert "python_version" in data

def test_api_v1_health_endpoint(client):
    """Verify that /api/v1/health probe reports services and cache connectivity."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["cache_connected"] is True
    assert "services" in data
    assert data["services"]["orchestrator"] == "available"

def test_analyze_endpoint_prewarmed_seed(client):
    """Verify that lifespan startup pre-warms seed sentences to eliminate cold-start lag."""
    payload = {"text": "बालकः पुस्तकं पठति।"}
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["cached"] is True
    assert len(data["sandhi_splits"]) >= 3
    assert len(data["morphology"]) >= 3

def test_analyze_endpoint_cold_success(client):
    """Verify that POST /api/v1/analyze executes the full pipeline end-to-end on un-cached text."""
    payload = {"text": "छात्राः क्रीडाक्षेत्रे धावन्ति।"}
    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["original_text"] == "छात्राः क्रीडाक्षेत्रे धावन्ति।"
    assert data["normalized_text"] == "छात्राः क्रीडाक्षेत्रे धावन्ति।"
    assert len(data["sandhi_splits"]) >= 3
    assert len(data["morphology"]) >= 3
    assert len(data["translation"]) > 0
    assert data["cached"] is False
    assert data["processing_time_ms"] >= 0.0

def test_analyze_endpoint_cached_response(client):
    """Verify that repeated queries hit the cache and return cached=True."""
    payload = {"text": "सूर्यः आकाशे प्रकाशते।"}
    
    # Initial request (cold)
    res1 = client.post("/api/v1/analyze", json=payload)
    assert res1.status_code == 200
    assert res1.json()["cached"] is False

    # Repeated request (hot cache)
    res2 = client.post("/api/v1/analyze", json=payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["cached"] is True
    assert data2["translation"] == res1.json()["translation"]

def test_analyze_batch_endpoint_success(client):
    """Verify that POST /api/v1/analyze/batch processes multiple sentences concurrently."""
    payload = {
        "sentences": [
            "बालकः पुस्तकं पठति।",
            "छात्राः क्रीडाक्षेत्रे धावन्ति।",
            "वयं विद्यालये पठामः।"
        ]
    }
    response = client.post("/api/v1/analyze/batch", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["total_sentences"] == 3
    assert len(data["results"]) == 3
    assert data["total_processing_time_ms"] > 0.0
    for res in data["results"]:
        assert len(res["sandhi_splits"]) > 0
        assert len(res["morphology"]) > 0
        assert len(res["translation"]) > 0

def test_analyze_batch_endpoint_empty(client):
    """Verify that empty batch list returns 400 Bad Request."""
    response = client.post("/api/v1/analyze/batch", json={"sentences": []})
    assert response.status_code in [400, 422]

def test_gzip_compression_on_large_payload(client):
    """Verify GZip compression middleware compresses large payloads (> 1000 bytes)."""
    payload = {
        "sentences": [
            "बालकः पुस्तकं पठति।",
            "छात्राः क्रीडाक्षेत्रे धावन्ति।",
            "वयं विद्यालये पठामः।"
        ]
    }
    response = client.post(
        "/api/v1/analyze/batch",
        json=payload,
        headers={"Accept-Encoding": "gzip"},
    )
    assert response.status_code == 200
    # Responses > 1000 bytes should be gzipped
    assert response.headers.get("content-encoding") == "gzip"

def test_analyze_endpoint_bypass_cache(client):
    """Verify that bypass_cache=True forces re-computation."""
    payload = {"text": "सत्यं वद।"}
    client.post("/api/v1/analyze", json=payload)

    res_bypass = client.post("/api/v1/analyze?bypass_cache=true", json=payload)
    assert res_bypass.status_code == 200
    assert res_bypass.json()["cached"] is False

def test_analyze_endpoint_empty_input(client):
    """Verify that empty string returns 400 Bad Request."""
    response = client.post("/api/v1/analyze", json={"text": "   "})
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

def test_morphology_endpoint_success(client):
    """Verify that POST /api/v1/morphology analyzes token sequences directly."""
    payload = {"tokens": ["बालकः", "पुस्तकम्", "पठति"]}
    response = client.post("/api/v1/morphology", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 3
    assert data[0]["word"] == "बालकः"
    assert data[0]["primary_gloss"]["root"] != ""
    assert data[0]["primary_gloss"]["pos"] != ""
    assert "प्रथमा" in data[0]["primary_gloss"]["case"] or "Nominative" in data[0]["primary_gloss"]["case"]

def test_morphology_endpoint_empty(client):
    """Verify that empty token list returns 400 or 422."""
    response = client.post("/api/v1/morphology", json={"tokens": []})
    assert response.status_code in [400, 422]

def test_cache_stats_and_clear_endpoints(client):
    """Verify cache statistics retrieval and clear actions."""
    stats_res = client.get("/api/v1/cache/stats")
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert "total_cached_sentences" in stats_data

    clear_res = client.post("/api/v1/cache/clear")
    assert clear_res.status_code == 200
    assert "cleared" in clear_res.json()["message"].lower()

def test_cors_headers(client):
    """Verify that CORS preflight and origin headers are accepted."""
    headers = {
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
    }
    response = client.options("/api/v1/analyze", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
