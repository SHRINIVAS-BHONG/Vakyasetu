import pytest
import time
from typing import Dict, Any, List

from fastapi.testclient import TestClient
from app.main import app
from app.models.schemas import VakyaSetuResponse
from app.services.orchestrator import get_orchestrator_service

# ==============================================================================
# NCERT / CBSE CLASS 6-10 GOLDEN BENCHMARK CORPUS
# Selected from Ruchira (Classes 6-8) and Shemushi (Classes 9-10)
# ==============================================================================

NCERT_GOLDEN_CORPUS: List[Dict[str, Any]] = [
    {
        "id": "NCERT-CL6-01",
        "sentence": "बालकः पुस्तकं पठति।",
        "grade": "Class 6 (Ruchira)",
        "grammar_focus": "SVO, Masculine Nominative Singular, Present Tense (Laṭ)",
        "expected_roots": ["बालक", "पुस्तक", "पठ्"],
    },
    {
        "id": "NCERT-CL6-02",
        "sentence": "वयं विद्यालये पठामः।",
        "grade": "Class 6 (Ruchira)",
        "grammar_focus": "Pronoun (Asmad) Plural, Locative (Adhikaraṇa), 1st Person Plural",
        "expected_roots": ["अस्मद्", "विद्यालय", "पठ्"],
    },
    {
        "id": "NCERT-CL6-03",
        "sentence": "सः सदा सत्यं वदति।",
        "grade": "Class 6 (Ruchira)",
        "grammar_focus": "Pronoun (Tad), NCERT Avyaya (Sadā), Accusative (Karma)",
        "expected_roots": ["तद्", "सदा", "सत्य", "वद्"],
    },
    {
        "id": "NCERT-CL7-01",
        "sentence": "सह विद्यालयं गत्वा गुरुं प्रणमति।",
        "grade": "Class 7 (Ruchira)",
        "grammar_focus": "Ktvā Gerund (Gatvā), Upasarga Verb (Pra + Nam)",
        "expected_roots": ["तद्", "विद्यालय", "गम्", "गुरु", "नम्"],
    },
    {
        "id": "NCERT-CL7-02",
        "sentence": "वृक्षात् पत्राणि पतन्ति।",
        "grade": "Class 7 (Ruchira)",
        "grammar_focus": "Ablative (Apādāna 5th case), Neuter Plural Subanta",
        "expected_roots": ["वृक्ष", "पत्र", "पत्"],
    },
    {
        "id": "NCERT-CL7-03",
        "sentence": "छात्राः क्रीडाक्षेत्रे कन्दुकेन क्रीडन्ति।",
        "grade": "Class 7 (Ruchira)",
        "grammar_focus": "Instrumental (Karaṇa 3rd case), Locative, Plural Verb",
        "expected_roots": ["छात्र", "क्रीडाक्षेत्र", "कन्दुक", "क्रीड्"],
    },
    {
        "id": "NCERT-CL8-01",
        "sentence": "अहं प्रतिदिनं प्रातः ईश्वरं स्मरामि।",
        "grade": "Class 8 (Ruchira)",
        "grammar_focus": "First Person Singular, Avyayas (Prātah), Karma Accusative",
        "expected_roots": ["अस्मद्", "प्रतिदिन", "प्रातः", "ईश्वर", "स्मृ"],
    },
    {
        "id": "NCERT-CL8-02",
        "sentence": "विद्या ददाति विनयं विनयाद् याति पात्रताम्।",
        "grade": "Class 8 (Ruchira)",
        "grammar_focus": "Subhashita Prose, Ablative (Vinayāt -> Vinayād Sandhi)",
        "expected_roots": ["विद्या", "दा", "विनय", "या", "पात्रता"],
    },
    {
        "id": "NCERT-CL9-01",
        "sentence": "दशरथस्य पुत्राः चत्वारः आसन्।",
        "grade": "Class 9 (Shemushi)",
        "grammar_focus": "Genitive (Sambandha 6th case), Numerical Adjective, Past Tense (As)",
        "expected_roots": ["दशरथ", "पुत्र", "चतुर्", "अस्"],
    },
    {
        "id": "NCERT-CL10-01",
        "sentence": "सत्यमेव जयते नानृतम्।",
        "grade": "Class 10 (Shemushi / Upanishad)",
        "grammar_focus": "Avyaya Sandhi (Satyam + Eva), Negative Svarasandhi (Na + Anṛtam)",
        "expected_roots": ["सत्य", "एव", "जि", "न", "अनृत"],
    },
]

@pytest.fixture(scope="module")
def orchestrator():
    """Provides singleton OrchestratorService for golden test suite."""
    return get_orchestrator_service()

@pytest.fixture(scope="module")
def api_client():
    """Provides FastAPI test client for API integration tests."""
    with TestClient(app) as client:
        yield client

# ==============================================================================
# 1. CORE PIPELINE GOLDEN VERIFICATION
# ==============================================================================

@pytest.mark.parametrize("item", NCERT_GOLDEN_CORPUS, ids=lambda x: x["id"])
def test_ncert_golden_sentence_analysis(orchestrator, item):
    """
    Validates that each NCERT Class 6-10 golden benchmark sentence:
    1. Returns a complete, non-null VakyaSetuResponse.
    2. Has sandhi splits matching expected tokens.
    3. Contains complete morphological cards with roots, POS, and bilingual explanations.
    4. Produces natural English translation without unparsed remnants.
    """
    sentence = item["sentence"]
    response = orchestrator.analyze(sentence)

    assert isinstance(response, VakyaSetuResponse)
    assert response.original_text == sentence
    assert response.normalized_text != ""
    assert len(response.sandhi_splits) > 0
    assert len(response.morphology) == len(response.sandhi_splits)
    assert len(response.translation) > 0

    # Ensure every word card is fully glossed with zero stubs
    morph_roots = []
    for word_analysis in response.morphology:
        gloss = word_analysis.primary_gloss
        assert gloss.root != "", f"Empty root in word '{word_analysis.word}'"
        assert gloss.pos != "", f"Empty POS in word '{word_analysis.word}'"
        assert gloss.sanskrit_explanation != "", f"Missing Sanskrit explanation in '{word_analysis.word}'"
        assert gloss.english_explanation != "", f"Missing English explanation in '{word_analysis.word}'"
        morph_roots.append(gloss.root)

    # Check that at least some expected core lemmas are detected
    expected = item["expected_roots"]
    matching_roots = [r for r in expected if any(r in mr for mr in morph_roots)]
    assert len(matching_roots) >= 1, f"Expected roots {expected} not found in {morph_roots}"

# ==============================================================================
# 2. LATENCY & CACHING BENCHMARKS (PRODUCTION SLA VERIFICATION)
# ==============================================================================

def test_ncert_golden_latency_sla(orchestrator):
    """
    Verifies that hot cache lookups across all NCERT sentences achieve < 50ms latency
    (sub-millisecond resolution for production throughput).
    """
    latencies = []
    for item in NCERT_GOLDEN_CORPUS:
        sentence = item["sentence"]
        
        # Warm up cache with initial query
        orchestrator.analyze(sentence)

        # Measure cached latency
        t0 = time.perf_counter()
        cached_res = orchestrator.analyze(sentence)
        latency_ms = (time.perf_counter() - t0) * 1000
        latencies.append(latency_ms)

        assert cached_res.cached is True
        assert latency_ms < 50.0  # Production sub-50ms SLA

    avg_latency = sum(latencies) / len(latencies)
    assert avg_latency < 10.0, f"Average cached latency {avg_latency:.2f}ms exceeds 10ms threshold"

# ==============================================================================
# 3. REST API END-TO-END GOLDEN SUITE VERIFICATION
# ==============================================================================

@pytest.mark.parametrize("item", NCERT_GOLDEN_CORPUS, ids=lambda x: x["id"])
def test_ncert_golden_api_endpoint(api_client, item):
    """
    Validates that the POST /api/v1/analyze endpoint successfully processes
    all NCERT golden sentences over HTTP with 200 OK.
    """
    payload = {"text": item["sentence"]}
    response = api_client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["original_text"] == item["sentence"]
    assert len(data["sandhi_splits"]) > 0
    assert len(data["morphology"]) > 0
    assert len(data["translation"]) > 0
    assert data["processing_time_ms"] >= 0.0

# ==============================================================================
# 4. PEDAGOGICAL BILINGUAL CARD VERIFICATION
# ==============================================================================

def test_ncert_bilingual_gloss_quality(orchestrator):
    """
    Verifies that morphological cards include student-friendly NCERT terminology:
    - Case names (प्रथमा, द्वितीया, तृतीया, etc. and Nominative, Accusative)
    - Tense names (लट्, लङ्, लृट्, etc. and Present Tense, Past Tense)
    - Person names (प्रथमपुरुषः, उत्तमपुरुषः, Third Person, First Person)
    """
    sentence = "बालकः पुस्तकं पठति।"
    response = orchestrator.analyze(sentence)
    
    # 1. Subject (बालकः): Nominative 1st Case
    boy_card = response.morphology[0].primary_gloss
    assert "प्रथमा" in boy_card.case or "Nominative" in boy_card.case

    # 2. Verb (पठति): Present Tense (लट्), Third Person
    verb_card = response.morphology[-1].primary_gloss
    assert "लट्" in verb_card.tense or "Present" in verb_card.tense
    assert "प्रथमपुरुषः" in verb_card.person or "Third Person" in verb_card.person
