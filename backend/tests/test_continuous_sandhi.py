import pytest
from app.services.sandhi import get_sandhi_service

@pytest.fixture(scope="module")
def sandhi():
    return get_sandhi_service()

def test_continuous_ramo_griham_gacchati(sandhi):
    """Accurately segments space-less 'रामोगृहंगच्छति' into 3 proper words without 'अगृहम्'."""
    res = sandhi.split("रामोगृहंगच्छति")
    assert res is not None
    assert res.split_words == ["रामः", "गृहम्", "गच्छति"]

def test_continuous_satyam_vada(sandhi):
    """Segments continuous 'सत्यंवद' into ['सत्यम्', 'वद'] without spurious 1-letter cuts."""
    res = sandhi.split("सत्यंवद")
    assert res is not None
    assert res.split_words == ["सत्यम्", "वद"]

def test_continuous_balakah_phalam_khadati(sandhi):
    """Segments unspaced 3-word sentence 'बालकःफलम्खादति'."""
    res = sandhi.split("बालकःफलम्खादति")
    assert res is not None
    assert res.split_words == ["बालकः", "फलम्", "खादति"]

def test_continuous_sandhi_rule_attribution(sandhi):
    """Verifies that Paninian sandhi rules (Utva visarga) are attributed on continuous text."""
    res = sandhi.split("रामोगृहंगच्छति")
    assert len(res.rules) > 0
    assert any("उत्वम्" in r.rule_name or "विसर्ग" in r.sandhi_type for r in res.rules)

def test_spaced_sentence_remains_intact(sandhi):
    """Standard spaced sentences remain 100% unaffected."""
    res = sandhi.split("बालकः फलम् खादति")
    assert res.split_words == ["बालकः", "फलम्", "खादति"]
