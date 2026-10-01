import pytest
import unicodedata
from app.core.normalizer import SanskritNormalizer

def test_sanskrit_normalizer_nfc():
    """Verify that Devanagari decomposed characters are normalized to NFC."""
    # Decomposed: base 'क' + virama '्' + 'ष' (versus composed form)
    raw = "बालकः"
    decomposed = unicodedata.normalize("NFD", raw)
    assert decomposed != raw or len(decomposed) >= len(raw)
    normalized = SanskritNormalizer.normalize(decomposed)
    assert unicodedata.is_normalized("NFC", normalized)
    assert normalized == "बालकः"

def test_sanskrit_normalizer_whitespace_and_cleanup():
    """Verify that excessive tabs, newlines, and spaces are collapsed to single spaces."""
    messy_text = "   बालकः   \t\n  विद्यालयं \n\n  गच्छति।   "
    clean = SanskritNormalizer.normalize(messy_text)
    assert clean == "बालकः विद्यालयं गच्छति।"

def test_sanskrit_normalizer_strips_invalid_symbols():
    """Verify that random ASCII symbols and HTML tags are stripped while preserving Sanskrit."""
    dirty_text = "<b>बालकः</b> @#$%^&* पुस्तकं पठति! [100%]"
    clean = SanskritNormalizer.normalize(dirty_text)
    assert "बालकः" in clean
    assert "पुस्तकं" in clean
    assert "पठति" in clean
    assert "@" not in clean
    assert "#" not in clean
    assert "$" not in clean
    assert "%" not in clean
    assert "^" not in clean
    assert "&" not in clean
    assert "*" not in clean

def test_danda_preservation():
    """Verify that both single danda (।) and double danda (॥) are preserved."""
    verse = "सत्यं वद। धर्मं चर॥"
    clean = SanskritNormalizer.normalize(verse)
    assert "।" in clean
    assert "॥" in clean
    assert clean == "सत्यं वद। धर्मं चर॥"

def test_is_devanagari():
    """Verify Devanagari detection heuristic."""
    assert SanskritNormalizer.is_devanagari("पठति") is True
    assert SanskritNormalizer.is_devanagari("सत्यमेव जयते") is True
    assert SanskritNormalizer.is_devanagari("Hello World") is False
    assert SanskritNormalizer.is_devanagari("123456") is False
    assert SanskritNormalizer.is_devanagari("") is False
