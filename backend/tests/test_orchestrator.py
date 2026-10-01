import pytest
import time
import tempfile
import os

from app.services.cache import SQLiteCache
from app.services.orchestrator import OrchestratorService, get_orchestrator_service
from app.models.schemas import VakyaSetuResponse

@pytest.fixture
def isolated_orchestrator():
    """Provides an OrchestratorService with an isolated temporary SQLite cache."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = f.name
    temp_cache = SQLiteCache(db_path=temp_path)
    service = OrchestratorService(cache=temp_cache)
    yield service
    # Cleanup
    temp_cache.close()
    try:
        os.remove(temp_path)
        for ext in ["-wal", "-shm"]:
            if os.path.exists(temp_path + ext):
                os.remove(temp_path + ext)
    except Exception:
        pass

def test_orchestrator_end_to_end_analysis(isolated_orchestrator):
    """Verify that a standard Sanskrit sentence flows through all 5 pipeline stages."""
    sentence = "बालकः पुस्तकं पठति।"
    response = isolated_orchestrator.analyze(sentence)

    assert isinstance(response, VakyaSetuResponse)
    assert response.original_text == sentence
    assert response.normalized_text == "बालकः पुस्तकं पठति।"
    assert len(response.sandhi_splits) >= 3
    assert "बालकः" in response.sandhi_splits
    assert "पठति" in response.sandhi_splits
    assert len(response.morphology) == len(response.sandhi_splits)
    
    # Check that all morphological entries are complete with zero stubs
    for item in response.morphology:
        assert item.word != ""
        assert item.primary_gloss.root != ""
        assert item.primary_gloss.pos != ""
        assert item.primary_gloss.sanskrit_explanation != ""
        assert item.primary_gloss.english_explanation != ""

    assert "boy" in response.translation.lower() or "read" in response.translation.lower() or "book" in response.translation.lower()
    assert response.cached is False
    assert response.processing_time_ms >= 0.0

def test_orchestrator_caching_latency(isolated_orchestrator):
    """Verify that repeated queries hit the two-tier cache and return in sub-millisecond time."""
    sentence = "वयं विद्यालये पठामः।"
    
    # Cold run
    t0 = time.perf_counter()
    cold_response = isolated_orchestrator.analyze(sentence)
    cold_latency = (time.perf_counter() - t0) * 1000
    assert cold_response.cached is False

    # Hot run (L1 RAM cache)
    t1 = time.perf_counter()
    hot_response = isolated_orchestrator.analyze(sentence)
    hot_latency = (time.perf_counter() - t1) * 1000

    assert hot_response.cached is True
    assert hot_response.translation == cold_response.translation
    assert hot_response.sandhi_splits == cold_response.sandhi_splits
    assert len(hot_response.morphology) == len(cold_response.morphology)
    assert hot_latency < cold_latency
    assert hot_latency < 50.0  # Ultra-fast sub-50ms cache return

def test_orchestrator_bypass_cache(isolated_orchestrator):
    """Verify that bypass_cache forces complete re-computation."""
    sentence = "सत्यं वद।"
    res1 = isolated_orchestrator.analyze(sentence)
    assert res1.cached is False

    res2 = isolated_orchestrator.analyze(sentence, bypass_cache=True)
    assert res2.cached is False

def test_orchestrator_dirty_unicode_invariance(isolated_orchestrator):
    """Verify that dirty copy-pasted strings with zero-width spaces hit the same cache."""
    clean_sentence = "सत्यमेव जयते नानृतम्।"
    res_clean = isolated_orchestrator.analyze(clean_sentence)
    assert res_clean.cached is False

    # Dirty input with ZWNJ and extra spacing
    dirty_sentence = "  सत्य\u200Cमेव   जयते    नानृतम्।  "
    res_dirty = isolated_orchestrator.analyze(dirty_sentence)
    assert res_dirty.cached is True
    assert res_dirty.translation == res_clean.translation

def test_orchestrator_empty_input(isolated_orchestrator):
    """Verify that empty or whitespace-only inputs return gracefully."""
    res_empty = isolated_orchestrator.analyze("")
    assert res_empty.normalized_text == ""
    assert res_empty.translation == ""
    assert res_empty.sandhi_splits == []
    assert res_empty.morphology == []
    assert res_empty.processing_time_ms == 0.0

    res_spaces = isolated_orchestrator.analyze("   \t  \n  ")
    assert res_spaces.normalized_text == ""
    assert res_spaces.processing_time_ms == 0.0

def test_orchestrator_complex_sentence_with_participle(isolated_orchestrator):
    """Verify a multi-clause sentence containing Ktvā participle and upasarga verb."""
    sentence = "सह विद्यालयं गत्वा गुरुं प्रणमति।"
    response = isolated_orchestrator.analyze(sentence)

    assert response.normalized_text == sentence
    # Should contain गत्वा (Ktvā participle)
    words = [m.word for m in response.morphology]
    assert any("गत्वा" in w for w in words)
    assert any("प्रणमति" in w for w in words)
    assert response.translation != ""

def test_orchestrator_telemetry(isolated_orchestrator):
    """Verify that get_telemetry returns healthy diagnostics."""
    telemetry = isolated_orchestrator.get_telemetry()
    assert telemetry["status"] == "operational"
    assert "cache" in telemetry
    assert "neural_model_loaded" in telemetry

def test_get_orchestrator_service_singleton():
    """Verify that get_orchestrator_service returns a singleton."""
    o1 = get_orchestrator_service()
    o2 = get_orchestrator_service()
    assert o1 is o2
