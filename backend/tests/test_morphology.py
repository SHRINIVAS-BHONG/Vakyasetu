import pytest
from app.services.morphology import MorphologyService

@pytest.fixture(scope="module")
def morphology_service():
    return MorphologyService()

# ==============================================================================
# 1. TEST ALL 5 CBSE / NCERT LAKĀRAS (लकाराः)
# ==============================================================================

def test_lat_lakara_present_tense(morphology_service):
    """Test लट् लकारः (Present Tense) for pathati and gacchati."""
    analysis = morphology_service.analyze_word("पठति")
    gloss = analysis.primary_gloss
    assert "Verb" in gloss.pos
    assert "पठ्" in gloss.root or "पठ" in gloss.root
    assert gloss.tense is not None and "Present" in gloss.tense
    assert gloss.person is not None and "Third" in gloss.person
    assert gloss.number is not None and "Singular" in gloss.number

    analysis2 = morphology_service.analyze_word("गच्छति")
    gloss2 = analysis2.primary_gloss
    assert "Verb" in gloss2.pos
    assert "गम्" in gloss2.root or "गम" in gloss2.root
    assert "Present" in gloss2.tense
    assert "Singular" in gloss2.number

def test_lan_lakara_past_tense(morphology_service):
    """Test लङ् लकारः (Past Imperfect Tense) for apathat and agacchāt."""
    analysis = morphology_service.analyze_word("अपठत्")
    gloss = analysis.primary_gloss
    assert "Verb" in gloss.pos
    assert "पठ्" in gloss.root or "पठ" in gloss.root
    assert gloss.tense is not None and ("Past" in gloss.tense or "लङ्" in gloss.tense)
    assert gloss.number is not None and "Singular" in gloss.number

    analysis2 = morphology_service.analyze_word("अगच्छत्")
    gloss2 = analysis2.primary_gloss
    assert "Verb" in gloss2.pos
    assert "गम्" in gloss2.root or "गम" in gloss2.root
    assert "Past" in gloss2.tense or "लङ्" in gloss2.tense

def test_lrt_lakara_future_tense(morphology_service):
    """Test लृट् लकारः (Simple Future Tense) for pathisyati and gamisyati."""
    analysis = morphology_service.analyze_word("पठिष्यति")
    gloss = analysis.primary_gloss
    assert "Verb" in gloss.pos
    assert "पठ्" in gloss.root or "पठ" in gloss.root
    assert gloss.tense is not None and ("Future" in gloss.tense or "लृट्" in gloss.tense)

    analysis2 = morphology_service.analyze_word("गमिष्यति")
    gloss2 = analysis2.primary_gloss
    assert "Verb" in gloss2.pos
    assert "गम्" in gloss2.root or "गम" in gloss2.root
    assert "Future" in gloss2.tense or "लृट्" in gloss2.tense

def test_lot_lakara_imperative(morphology_service):
    """Test लोट् लकारः (Imperative Mood) for pathatu and gacchatu."""
    analysis = morphology_service.analyze_word("पठतु")
    gloss = analysis.primary_gloss
    assert "Verb" in gloss.pos
    assert "पठ्" in gloss.root or "पठ" in gloss.root
    assert gloss.tense is not None and ("Imperative" in gloss.tense or "लोट्" in gloss.tense)

    analysis2 = morphology_service.analyze_word("गच्छतु")
    gloss2 = analysis2.primary_gloss
    assert "Verb" in gloss2.pos
    assert "गम्" in gloss2.root or "गम" in gloss2.root
    assert "Imperative" in gloss2.tense or "लोट्" in gloss2.tense

def test_vidhilin_lakara_potential(morphology_service):
    """Test विधिलिङ् लकारः (Potential / Optative Mood) for pathet and gaccheti."""
    analysis = morphology_service.analyze_word("पठेत्")
    gloss = analysis.primary_gloss
    assert "Verb" in gloss.pos
    assert "पठ्" in gloss.root or "पठ" in gloss.root
    assert gloss.tense is not None and ("Potential" in gloss.tense or "विधिलिङ्" in gloss.tense)

    analysis2 = morphology_service.analyze_word("गच्छेत्")
    gloss2 = analysis2.primary_gloss
    assert "Verb" in gloss2.pos
    assert "गम्" in gloss2.root or "गम" in gloss2.root
    assert "Potential" in gloss2.tense or "विधिलिङ्" in gloss2.tense

# ==============================================================================
# 2. TEST UPASARGA (PREFIX) DECOMPOSITION
# ==============================================================================

def test_upasarga_verbs(morphology_service):
    """Test prefixed verbs with Upasarga stripping."""
    # प्रणमति -> pra + nam
    analysis_pranam = morphology_service.analyze_word("प्रणमति")
    gloss_pranam = analysis_pranam.primary_gloss
    assert "Verb" in gloss_pranam.pos
    assert "नम्" in gloss_pranam.root or "नम" in gloss_pranam.root
    assert gloss_pranam.prefix is not None and "प्र" in gloss_pranam.prefix

    # अनुगच्छति -> anu + gam
    analysis_anugam = morphology_service.analyze_word("अनुगच्छति")
    gloss_anugam = analysis_anugam.primary_gloss
    assert "Verb" in gloss_anugam.pos
    assert "गम्" in gloss_anugam.root or "गम" in gloss_anugam.root
    assert gloss_anugam.prefix is not None and "अनु" in gloss_anugam.prefix

    # विहरति -> vi + hr
    analysis_vihar = morphology_service.analyze_word("विहरति")
    gloss_vihar = analysis_vihar.primary_gloss
    assert "Verb" in gloss_vihar.pos
    assert "हृ" in gloss_vihar.root or "हर" in gloss_vihar.root
    assert gloss_vihar.prefix is not None and "वि" in gloss_vihar.prefix

# ==============================================================================
# 3. TEST KṚDANTA (PARTICIPLES) WITH PRATYAYAS
# ==============================================================================

def test_participle_ktva(morphology_service):
    """Test क्त्वा प्रत्ययः (having done / gerund)."""
    analysis = morphology_service.analyze_word("गत्वा")
    gloss = analysis.primary_gloss
    assert "गम्" in gloss.root or "गम" in gloss.root
    assert "Participle" in gloss.pos or "कृदन्त" in gloss.pos
    assert gloss.pratyaya is not None and ("क्त्वा" in gloss.pratyaya or "Ktvā" in gloss.pratyaya)

    analysis_path = morphology_service.analyze_word("पठित्वा")
    gloss_path = analysis_path.primary_gloss
    assert "पठ्" in gloss_path.root or "पठ" in gloss_path.root
    assert gloss_path.pratyaya is not None and ("क्त्वा" in gloss_path.pratyaya or "Ktvā" in gloss_path.pratyaya)

def test_participle_lyap(morphology_service):
    """Test ल्यप् प्रत्ययः (having done with prefix)."""
    analysis = morphology_service.analyze_word("प्रणम्य")
    gloss = analysis.primary_gloss
    assert "नम्" in gloss.root or "नम" in gloss.root
    assert gloss.prefix is not None and "प्र" in gloss.prefix
    assert gloss.pratyaya is not None and ("ल्यप्" in gloss.pratyaya or "Lyap" in gloss.pratyaya)

def test_participle_tumun(morphology_service):
    """Test तुमुन् प्रत्ययः (infinitive)."""
    analysis = morphology_service.analyze_word("पठितुम्")
    gloss = analysis.primary_gloss
    assert "पठ्" in gloss.root or "पठ" in gloss.root
    assert gloss.pratyaya is not None and ("तुमुन्" in gloss.pratyaya or "Tumun" in gloss.pratyaya)

    analysis_gantum = morphology_service.analyze_word("गन्तुम्")
    gloss_gantum = analysis_gantum.primary_gloss
    assert "गम्" in gloss_gantum.root or "गम" in gloss_gantum.root
    assert gloss_gantum.pratyaya is not None and ("तुमुन्" in gloss_gantum.pratyaya or "Tumun" in gloss_gantum.pratyaya)

def test_participle_ktavatu_and_kta(morphology_service):
    """Test क्तवतु (past active) and क्त (past passive) participles."""
    # गतवान्
    analysis_gatavan = morphology_service.analyze_word("गतवान्")
    gloss_gatavan = analysis_gatavan.primary_gloss
    assert "गम्" in gloss_gatavan.root or "गत" in gloss_gatavan.root
    assert gloss_gatavan.pratyaya is not None and ("क्तवतु" in gloss_gatavan.pratyaya or "Ktavatu" in gloss_gatavan.pratyaya)
    assert gloss_gatavan.voice is not None and "Active" in gloss_gatavan.voice

    # पठितः
    analysis_pathita = morphology_service.analyze_word("पठितः")
    gloss_pathita = analysis_pathita.primary_gloss
    assert "पठ्" in gloss_pathita.root or "पठ" in gloss_pathita.root
    assert gloss_pathita.pratyaya is not None and ("क्त" in gloss_pathita.pratyaya or "Kta" in gloss_pathita.pratyaya)

# ==============================================================================
# 4. TEST SUBANTA (NOUNS, PRONOUNS, DECLENSIONS)
# ==============================================================================

def test_noun_declensions_cases_1_to_7(morphology_service):
    """Test all 7 Vibhaktis for nominal forms."""
    # 1st case: बालकः
    g1 = morphology_service.analyze_word("बालकः").primary_gloss
    assert "बालक" in g1.root
    assert "Nominative" in (g1.case or "") or "प्रथमा" in (g1.case or "")

    # 2nd case: पुस्तकम्
    g2 = morphology_service.analyze_word("पुस्तकम्").primary_gloss
    assert "पुस्तक" in g2.root
    assert "Accusative" in (g2.case or "") or "द्वितीया" in (g2.case or "") or "Nominative" in (g2.case or "")

    # 3rd case: बालकेन
    g3 = morphology_service.analyze_word("बालकेन").primary_gloss
    assert "Instrumental" in (g3.case or "") or "तृतीया" in (g3.case or "")

    # 4th case: बालकाय
    g4 = morphology_service.analyze_word("बालकाय").primary_gloss
    assert "Dative" in (g4.case or "") or "चतुर्थी" in (g4.case or "")

    # 5th case: बालकात्
    g5 = morphology_service.analyze_word("बालकात्").primary_gloss
    assert "Ablative" in (g5.case or "") or "पञ्चमी" in (g5.case or "")

    # 6th case: बालकस्य
    g6 = morphology_service.analyze_word("बालकस्य").primary_gloss
    assert "Genitive" in (g6.case or "") or "षष्ठी" in (g6.case or "")

    # 7th case: बालकेषु
    g7 = morphology_service.analyze_word("बालकेषु").primary_gloss
    assert "Locative" in (g7.case or "") or "सप्तमी" in (g7.case or "")

def test_feminine_and_neuter_subanta(morphology_service):
    """Test feminine ākārānta and neuter plural forms."""
    # लतायाः (Genitive/Ablative feminine)
    g_lata = morphology_service.analyze_word("लतायाः").primary_gloss
    assert "लता" in g_lata.root
    assert "Feminine" in (g_lata.gender or "") or "स्त्रीलिङ्गम्" in (g_lata.gender or "")

    # पुस्तकानि (Neuter plural nominative/accusative)
    g_pustakani = morphology_service.analyze_word("पुस्तकानि").primary_gloss
    assert "पुस्तक" in g_pustakani.root
    assert "Plural" in (g_pustakani.number or "") or "बहुवचनम्" in (g_pustakani.number or "")

def test_pronouns(morphology_service):
    """Test personal pronouns वयम् and अहम्."""
    g_vayam = morphology_service.analyze_word("वयम्").primary_gloss
    assert "Pronoun" in g_vayam.pos or "अस्मद्" in g_vayam.root

    g_aham = morphology_service.analyze_word("अहम्").primary_gloss
    assert "Pronoun" in g_aham.pos or "अस्मद्" in g_aham.root

# ==============================================================================
# 5. TEST NCERT AVYAYAS (INDECLINABLES)
# ==============================================================================

def test_avyayas(morphology_service):
    """Test standard CBSE/NCERT indeclinables."""
    for word in ["सदा", "अपि", "च", "अत्र", "तत्र", "विना", "सह", "यदि"]:
        analysis = morphology_service.analyze_word(word)
        gloss = analysis.primary_gloss
        assert "Indeclinable" in gloss.pos or "अव्यय" in gloss.pos
        assert word in gloss.root

# ==============================================================================
# 6. TEST PEDAGOGICAL EXPLANATIONS & SEQUENCE
# ==============================================================================

def test_pedagogical_explanations(morphology_service):
    """Verify that both Sanskrit and English explanations are rich and populated."""
    analysis = morphology_service.analyze_word("पठति")
    gloss = analysis.primary_gloss
    assert len(gloss.sanskrit_explanation) > 10
    assert len(gloss.english_explanation) > 10
    assert "पठ्" in gloss.sanskrit_explanation or "पठ" in gloss.sanskrit_explanation
    assert "Root" in gloss.english_explanation or "Verb" in gloss.english_explanation

def test_analyze_tokens_sequence(morphology_service):
    """Verify multi-token sentence analysis."""
    tokens = ["बालकः", "पुस्तकम्", "पठति"]
    results = morphology_service.analyze_tokens(tokens)
    assert len(results) == 3
    assert results[0].word == "बालकः"
    assert results[1].word == "पुस्तकम्"
    assert results[2].word == "पठति"
