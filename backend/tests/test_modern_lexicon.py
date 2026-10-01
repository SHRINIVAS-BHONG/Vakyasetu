import pytest
from app.services.orchestrator import get_orchestrator_service
from app.services.morphology import get_morphology_service

@pytest.fixture(scope="module")
def morph():
    return get_morphology_service()

@pytest.fixture(scope="module")
def orch():
    return get_orchestrator_service()

def test_modern_terms_direct_lookup(morph):
    """Direct canonical modern Sanskrit terms must be recognized with modern noun POS."""
    terms = ["सङ्गणकम्", "चलदूरभाषः", "अन्तर्जालम्", "धूमशकटम्", "दूरदर्शनम्", "कार्यालयः"]
    for term in terms:
        res = morph.analyze_word(term)
        assert res.primary_gloss.root is not None
        assert "Modern Noun" in res.primary_gloss.pos
        assert res.confidence >= 0.95

def test_modern_loanwords_direct_lookup(morph):
    """Modern loanwords written in Devanagari must be recognized."""
    loanwords = ["कम्प्यूटरम्", "मोबाइल्", "इण्टरनेटम्", "ईमेल्", "सॉफ्टवेयर्"]
    for word in loanwords:
        res = morph.analyze_word(word)
        assert res.primary_gloss.root is not None
        assert "Modern Noun" in res.primary_gloss.pos

def test_modern_inflected_forms(morph):
    """Inflected modern terms must accurately decouple case and number."""
    test_cases = [
        ("सङ्गणकेन", "Instrumental (3rd Case)"),
        ("कम्प्यूटरेण", "Instrumental (3rd Case)"),
        ("मोबाइलेन", "Instrumental (3rd Case)"),
        ("रेलयानस्य", "Genitive (6th Case)"),
        ("इण्टरनेटे", "Locative (7th Case)"),
        ("कार्यालये", "Locative (7th Case)"),
        ("सङ्गणकात्", "Ablative (5th Case)"),
    ]
    for token, expected_case in test_cases:
        res = morph.analyze_word(token)
        assert res.primary_gloss.case is not None
        assert expected_case in res.primary_gloss.case, f"Expected {expected_case} in {res.primary_gloss.case} for {token}"
        assert "Modern Noun" in res.primary_gloss.pos

def test_modern_sentences_end_to_end(orch):
    """Modern student sentences must analyze completely without unhandled errors."""
    s1 = "अहं सङ्गणकेन कार्यं करोमि।"
    r1 = orch.analyze(s1, bypass_cache=True)
    comp_word = next(w for w in r1.morphology if "सङ्गणके" in w.word)
    assert "Instrumental" in comp_word.primary_gloss.case
    assert comp_word.karaka_role in ["करणम् (Instrument)", "करणम्"]

    s2 = "सः मोबाइलेन वार्तां करोति।"
    r2 = orch.analyze(s2, bypass_cache=True)
    mob_word = next(w for w in r2.morphology if "मोबाइले" in w.word)
    assert "Instrumental" in mob_word.primary_gloss.case

    s3 = "छात्राः इण्टरनेटे पाठं पठन्ति।"
    r3 = orch.analyze(s3, bypass_cache=True)
    net_word = next(w for w in r3.morphology if "इण्टरनेट" in w.word)
    assert "Locative" in net_word.primary_gloss.case
