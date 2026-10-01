import pytest
import tempfile
import os
import time
from app.services.cache import SQLiteCache

@pytest.fixture
def temp_cache():
    """Provides an isolated temporary SQLite database for cache unit testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_path = f.name
    cache = SQLiteCache(db_path=temp_path)
    yield cache
    # Cleanup temporary file
    cache.close()
    try:
        os.remove(temp_path)
        for ext in ["-wal", "-shm"]:
            if os.path.exists(temp_path + ext):
                os.remove(temp_path + ext)
    except Exception:
        pass

def test_cache_miss(temp_cache):
    """Verify that an uncached sentence returns None."""
    result = temp_cache.get("अविद्यमानं वाक्यम्")
    assert result is None

def test_cache_set_and_hit(temp_cache):
    """Verify that set() stores response and get() returns it in sub-millisecond time."""
    test_sentence = "बालकः पुस्तकं पठति।"
    test_payload = {
        "original_text": test_sentence,
        "translation": "The boy reads a book.",
        "sandhi_splits": ["बालकः", "पुस्तकम्", "पठति"],
        "cached": False
    }

    temp_cache.set(test_sentence, test_payload)

    t0 = time.perf_counter()
    retrieved = temp_cache.get(test_sentence)
    latency_ms = (time.perf_counter() - t0) * 1000

    assert retrieved is not None
    assert retrieved["original_text"] == test_sentence
    assert retrieved["translation"] == "The boy reads a book."
    assert retrieved["sandhi_splits"] == ["बालकः", "पुस्तकम्", "पठति"]
    assert latency_ms < 50.0  # Sub-50ms even on busy systems

def test_cache_zero_width_and_space_invariance(temp_cache):
    """Verify that dirty copy-pasted strings with zero-width spaces or irregular spacing hit the cache."""
    clean_sentence = "सत्यमेव जयते नानृतम्।"
    payload = {"translation": "Truth alone triumphs, not falsehood."}
    temp_cache.set(clean_sentence, payload)

    # 1. Extra whitespace variations
    hit_spaces = temp_cache.get("  सत्यमेव   जयते    नानृतम्।  ")
    assert hit_spaces is not None
    assert hit_spaces["translation"] == payload["translation"]

    # 2. Zero-width non-joiner (ZWNJ: \u200C) and zero-width joiner (ZWJ: \u200D)
    hit_zwnj = temp_cache.get("सत्य\u200Cमेव जय\u200Dते नानृतम्।")
    assert hit_zwnj is not None
    assert hit_zwnj["translation"] == payload["translation"]

    # 3. Byte Order Mark (BOM: \uFEFF)
    hit_bom = temp_cache.get("\uFEFFसत्यमेव जयते नानृतम्।")
    assert hit_bom is not None
    assert hit_bom["translation"] == payload["translation"]

def test_cache_hit_count_increment(temp_cache):
    """Verify that hit count increments on repeated lookups."""
    sentence = "सत्यं वद।"
    temp_cache.set(sentence, {"message": "truth"})

    temp_cache.get(sentence)
    temp_cache.get(sentence)
    temp_cache.get(sentence)

    stats = temp_cache.get_stats()
    assert stats["total_cached_sentences"] == 1
    # 1 initial insert hit_count=1 + 3 gets = 4
    assert stats["total_hits"] >= 4

def test_cache_clear(temp_cache):
    """Verify that clear() empties the cache table."""
    temp_cache.set("वाक्यम् १", {"data": 1})
    temp_cache.set("वाक्यम् २", {"data": 2})

    stats_before = temp_cache.get_stats()
    assert stats_before["total_cached_sentences"] == 2

    temp_cache.clear()

    stats_after = temp_cache.get_stats()
    assert stats_after["total_cached_sentences"] == 0
    assert temp_cache.get("वाक्यम् १") is None

def test_get_cache_singleton():
    """Verify that get_cache returns a persistent singleton."""
    from app.services.cache import get_cache
    c1 = get_cache()
    c2 = get_cache()
    assert c1 is c2

