import pytest
from app.services.morphology import MorphologyService

@pytest.fixture(scope="module")
def morphology_service():
    return MorphologyService()

def test_fallback_proper_nouns_out_of_lexicon(morphology_service):
    """
    Test that historical/geographical proper nouns not in classical Heritage lexicon
    are resolved deterministically by the Paninian inflectional suffix matcher.
    """
    # कालिदासस्य (Kalidasa's -> Genitive)
    res1 = morphology_service._fallback_analysis("कालिदासस्य")
    g1 = res1.primary_gloss
    assert "कालिदास" in g1.root
    assert "Genitive" in (g1.case or "") or "षष्ठी" in (g1.case or "")
    assert "Noun" in g1.pos
    assert res1.confidence >= 0.85

    # विवेकानन्देन (By Vivekananda -> Instrumental)
    res2 = morphology_service._fallback_analysis("विवेकानन्देन")
    g2 = res2.primary_gloss
    assert "विवेकानन्द" in g2.root
    assert "Instrumental" in (g2.case or "") or "तृतीया" in (g2.case or "")

    # दिल्लीनगरे (In Delhi city -> Locative)
    res3 = morphology_service._fallback_analysis("दिल्लीनगरे")
    g3 = res3.primary_gloss
    assert "दिल्लीनगर" in g3.root
    assert "Locative" in (g3.case or "") or "सप्तमी" in (g3.case or "")

def test_fallback_all_five_lakaras(morphology_service):
    """
    Test deterministic verb conjugation matching across all 5 NCERT Lakāras in fallback mode.
    """
    # 1. Laṭ (Present): खेलति (plays)
    res_lat = morphology_service._fallback_analysis("खेलति")
    assert "Present" in (res_lat.primary_gloss.tense or "") or "लट्" in (res_lat.primary_gloss.tense or "")
    assert "Third" in (res_lat.primary_gloss.person or "")

    # 2. Laṅ (Past Imperfect): अखेलत् (played)
    res_lan = morphology_service._fallback_analysis("अखेलत्")
    assert "Past" in (res_lan.primary_gloss.tense or "") or "लङ्" in (res_lan.primary_gloss.tense or "")
    assert "Third" in (res_lan.primary_gloss.person or "")

    # 3. Lṛṭ (Future): खेलिष्यति (will play)
    res_lrt = morphology_service._fallback_analysis("खेलिष्यति")
    assert "Future" in (res_lrt.primary_gloss.tense or "") or "लृट्" in (res_lrt.primary_gloss.tense or "")

    # 4. Loṭ (Imperative): खेलतु (let him play)
    res_lot = morphology_service._fallback_analysis("खेलतु")
    assert "Imperative" in (res_lot.primary_gloss.tense or "") or "लोट्" in (res_lot.primary_gloss.tense or "")

    # 5. Vidhiliṅ (Potential): खेलेत् (should play)
    res_vidhi = morphology_service._fallback_analysis("खेलेत्")
    assert "Potential" in (res_vidhi.primary_gloss.tense or "") or "विधिलिङ्" in (res_vidhi.primary_gloss.tense or "")

def test_fallback_krdanta_participles(morphology_service):
    """
    Test fallback detection of participles: Ktvā, Lyap, Tumun, Ktavatu, Kta, Tavyat, Anīyar.
    """
    # Ktvā: खेलित्वा (having played)
    res_ktva = morphology_service._fallback_analysis("खेलित्वा")
    assert "Ktvā" in (res_ktva.primary_gloss.pratyaya or "") or "क्त्वा" in (res_ktva.primary_gloss.pratyaya or "")

    # Lyap with Upasarga: सम्पूज्य (having worshipped)
    res_lyap = morphology_service._fallback_analysis("सम्पूज्य")
    assert "Lyap" in (res_lyap.primary_gloss.pratyaya or "") or "ल्यप्" in (res_lyap.primary_gloss.pratyaya or "")
    assert res_lyap.primary_gloss.prefix == "सम्"

    # Tumun: खेलितुम् (in order to play)
    res_tumun = morphology_service._fallback_analysis("खेलितुम्")
    assert "Tumun" in (res_tumun.primary_gloss.pratyaya or "") or "तुमुन्" in (res_tumun.primary_gloss.pratyaya or "")

    # Ktavatu: खेलितवान् (played - past active)
    res_ktavatu = morphology_service._fallback_analysis("खेलितवान्")
    assert "Ktavatu" in (res_ktavatu.primary_gloss.pratyaya or "") or "क्तवतु" in (res_ktavatu.primary_gloss.pratyaya or "")
    assert "Active" in (res_ktavatu.primary_gloss.voice or "")

    # Tavyat: खेलितव्यम् (ought to be played)
    res_tavya = morphology_service._fallback_analysis("खेलितव्यम्")
    assert "Tavyat" in (res_tavya.primary_gloss.pratyaya or "") or "तव्यत्" in (res_tavya.primary_gloss.pratyaya or "")

def test_fallback_subanta_declensions(morphology_service):
    """
    Test dual, plural, feminine, and oblique noun cases in fallback mode.
    """
    # Dual: बालकाभ्याम् (by/for/from two boys)
    res_dual = morphology_service._fallback_analysis("बालकाभ्याम्")
    assert "Dual" in (res_dual.primary_gloss.number or "") or "द्विवचनम्" in (res_dual.primary_gloss.number or "")

    # Plural 6th: छात्राणाम् (of students)
    res_gen_pl = morphology_service._fallback_analysis("छात्राणाम्")
    assert "Genitive" in (res_gen_pl.primary_gloss.case or "") or "षष्ठी" in (res_gen_pl.primary_gloss.case or "")
    assert "Plural" in (res_gen_pl.primary_gloss.number or "")

    # Feminine 7th: पाठशालायाम् (in the school)
    res_fem_loc = morphology_service._fallback_analysis("पाठशालायाम्")
    assert "Locative" in (res_fem_loc.primary_gloss.case or "") or "सप्तमी" in (res_fem_loc.primary_gloss.case or "")
    assert "Feminine" in (res_fem_loc.primary_gloss.gender or "")

    # Neuter plural: मित्राणि (friends)
    res_neut_pl = morphology_service._fallback_analysis("मित्राणि")
    assert "Plural" in (res_neut_pl.primary_gloss.number or "")
    assert "Neuter" in (res_neut_pl.primary_gloss.gender or "")

def test_fallback_universal_coverage(morphology_service):
    """
    Ensure that arbitrary Sanskrit words never return empty/None strings.
    """
    arbitrary_words = ["सूर्योदयः", "हिमालयस्य", "अधुना", "शान्तिनिकेतने"]
    for w in arbitrary_words:
        res = morphology_service.analyze_word(w)
        assert res.primary_gloss is not None
        assert res.primary_gloss.root != ""
        assert len(res.primary_gloss.sanskrit_explanation) > 0
        assert len(res.primary_gloss.english_explanation) > 0
