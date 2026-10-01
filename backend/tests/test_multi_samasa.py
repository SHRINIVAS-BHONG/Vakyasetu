import pytest
from app.services.samasa import get_samasa_service

@pytest.fixture(scope="module")
def samasa():
    return get_samasa_service()

def test_multi_member_dvandva_rama_lakshmana_bharata(samasa):
    """Decomposes 3-member Dvandva compound into constituent names."""
    res = samasa.analyze_compound("रामलक्ष्मणभरताः")
    assert res is not None
    assert "द्वन्द्व" in res.samasa_type
    assert len(res.components) >= 3
    assert "राम" in res.components
    assert "लक्ष्मण" in res.components
    assert "च" in res.vigraha_vakya

def test_multi_member_dvandva_surya_chandra_nakshatra(samasa):
    """Decomposes 3-member celestial Dvandva compound."""
    res = samasa.analyze_compound("सूर्यचन्द्रनक्षत्राणि")
    assert res is not None
    assert "द्वन्द्व" in res.samasa_type
    assert len(res.components) >= 3
    assert "सूर्य" in res.components
    assert "चन्द्र" in res.components

def test_multi_member_tatpurusha_mandahasa(samasa):
    """Decomposes 3+ member compound into hierarchical constituents."""
    res = samasa.analyze_compound("मन्दहासशोभितवदनम्")
    assert res is not None
    assert len(res.components) >= 3
    assert "बहुपद" in res.samasa_type or "समास" in res.samasa_type

def test_standard_2_member_compounds_unaffected(samasa):
    """Ensures existing standard CBSE compounds are completely unaffected."""
    res1 = samasa.analyze_compound("प्रतिदिनम्")
    assert res1.samasa_type == "अव्ययीभावः"
    assert res1.vigraha_vakya == "दिनं दिनं प्रति"

    res2 = samasa.analyze_compound("यथाशक्ति")
    assert res2.samasa_type == "अव्ययीभावः"
    assert res2.vigraha_vakya == "शक्तिम् अनतिक्रम्य"

    res3 = samasa.analyze_compound("मातापितरौ")
    assert "द्वन्द्व" in res3.samasa_type
