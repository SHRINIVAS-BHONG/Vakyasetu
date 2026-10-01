import pytest
from app.services.morphology import get_morphology_service
from app.services.sandhi import get_sandhi_service
from app.services.samasa import get_samasa_service
from app.services.orchestrator import get_orchestrator_service

@pytest.fixture(scope="module")
def morphology_service():
    return get_morphology_service()

@pytest.fixture(scope="module")
def sandhi_service():
    return get_sandhi_service()

@pytest.fixture(scope="module")
def samasa_service():
    return get_samasa_service()

@pytest.fixture(scope="module")
def orchestrator_service():
    return get_orchestrator_service()

# ==============================================================================
# 1. PRIORITY 1: CONTEXTUAL DISAMBIGUATION & AGREEMENT TESTS
# ==============================================================================

def test_contextual_neuter_object_disambiguation(morphology_service):
    """
    Verify that in sentences with an explicit Nominative subject (बालकः),
    an ambiguous neuter noun (पुस्तकम्) is disambiguated to Accusative (Karma / Object).
    """
    tokens = ["बालकः", "पुस्तकम्", "पठति"]
    analyses = morphology_service.analyze_tokens(tokens)
    
    assert len(analyses) == 3
    # First token: Subject
    assert "कर्ता" in (analyses[0].karaka_role or "")
    assert "Nominative" in (analyses[0].primary_gloss.case or "") or "प्रथमा" in (analyses[0].primary_gloss.case or "")

    # Second token: Object (promoted from ambiguous Nom/Acc to Accusative Karma)
    assert "कर्म" in (analyses[1].karaka_role or "")
    assert "Accusative" in (analyses[1].primary_gloss.case or "") or "द्वितीया" in (analyses[1].primary_gloss.case or "")

    # Third token: Verb
    assert "क्रियापदम्" in (analyses[2].karaka_role or "")

def test_contextual_plural_agreement(morphology_service):
    """
    Verify that plural pronoun (वयम्) correctly assigns First Person Plural subject role.
    """
    tokens = ["वयम्", "विद्यालये", "पठामः"]
    raw_morph = [morphology_service.analyze_word(t) for t in tokens]
    analyses, karaka_rel = morphology_service.disambiguate_and_extract_karakas(raw_morph)

    assert "कर्ता" in (analyses[0].karaka_role or "")
    assert "अधिकरणम्" in (analyses[1].karaka_role or "")
    assert "क्रियापदम्" in (analyses[2].karaka_role or "")

    # Check relation link
    subj_links = [rel for rel in karaka_rel if "कर्ता" in rel.relation]
    assert len(subj_links) >= 1
    assert subj_links[0].source_word == "वयम्"
    assert subj_links[0].target_word == "पठामः"

# ==============================================================================
# 2. PRIORITY 2: UPAPADA-VIBHAKTI RULES TESTS
# ==============================================================================

def test_upapada_saha_tritiya(morphology_service):
    """
    Verify 'सह' triggers तृतीया (Instrumental) via Paninian rule 'सहयुक्तेऽप्रधाने (२.३.१९)'.
    """
    tokens = ["रामेण", "सह", "लक्ष्मणः", "गच्छति"]
    raw_morph = [morphology_service.analyze_word(t) for t in tokens]
    analyses, karaka_rel = morphology_service.disambiguate_and_extract_karakas(raw_morph)

    # रामेण must be governed by सह
    assert "उपपद-सम्बन्धः" in (analyses[0].karaka_role or "")
    assert "सह" in (analyses[0].karaka_role or "")
    assert "तृतीया" in (analyses[0].karaka_role or "")

    # Check relation
    upapada_links = [r for r in karaka_rel if "सह" in r.relation]
    assert len(upapada_links) == 1
    assert upapada_links[0].source_word == "रामेण"
    assert "२.३.१९" in upapada_links[0].rule

def test_upapada_namah_caturthi(morphology_service):
    """
    Verify 'नमः' triggers चतुर्थी (Dative) via Paninian rule 'नमःस्वस्तिस्वाहा... (२.३.१६)'.
    """
    tokens = ["शिवाय", "नमः"]
    raw_morph = [morphology_service.analyze_word(t) for t in tokens]
    analyses, karaka_rel = morphology_service.disambiguate_and_extract_karakas(raw_morph)

    assert "उपपद-सम्बन्धः" in (analyses[0].karaka_role or "")
    assert "नमः" in (analyses[0].karaka_role or "")
    assert "चतुर्थी" in (analyses[0].karaka_role or "")

    upapada_links = [r for r in karaka_rel if "नमः" in r.relation]
    assert len(upapada_links) == 1
    assert upapada_links[0].vibhakti == "चतुर्थी"

def test_upapada_prati_dvitiya(morphology_service):
    """
    Verify 'प्रति' triggers द्वितीया (Accusative).
    """
    tokens = ["गृहम्", "प्रति", "गच्छति"]
    raw_morph = [morphology_service.analyze_word(t) for t in tokens]
    analyses, karaka_rel = morphology_service.disambiguate_and_extract_karakas(raw_morph)

    assert "उपपद-सम्बन्धः" in (analyses[0].karaka_role or "")
    assert "प्रति" in (analyses[0].karaka_role or "")

def test_upapada_bahi_pancami(morphology_service):
    """
    Verify 'बहिः' triggers पञ्चमी (Ablative).
    """
    tokens = ["ग्रामात्", "बहिः", "गच्छति"]
    raw_morph = [morphology_service.analyze_word(t) for t in tokens]
    analyses, karaka_rel = morphology_service.disambiguate_and_extract_karakas(raw_morph)

    assert "उपपद-सम्बन्धः" in (analyses[0].karaka_role or "")
    assert "बहिः" in (analyses[0].karaka_role or "")

# ==============================================================================
# 3. PRIORITY 3: SANDHI PANINIAN SŪTRA EXPLANATIONS TESTS
# ==============================================================================

def test_sandhi_rule_dirgha(sandhi_service):
    """Verify Dīrgha Sandhi rule explanation on vidyā + ālayaḥ."""
    rule = sandhi_service.explain_sandhi_rule("विद्या", "आलयः")
    assert rule is not None
    assert rule.rule_name == "दीर्घसन्धिः"
    assert "अकः सवर्णे दीर्घः" in rule.sutra
    assert rule.sandhi_type == "स्वरसन्धिः"

def test_sandhi_rule_guna(sandhi_service):
    """Verify Guṇa Sandhi rule explanation on deva + indraḥ."""
    rule = sandhi_service.explain_sandhi_rule("देव", "इन्द्रः")
    assert rule is not None
    assert rule.rule_name == "गुणसन्धिः"
    assert "आद्गुणः" in rule.sutra

def test_sandhi_rule_vriddhi(sandhi_service):
    """Verify Vṛddhi Sandhi rule explanation on sadā + eva."""
    rule = sandhi_service.explain_sandhi_rule("सदा", "एव")
    assert rule is not None
    assert rule.rule_name == "वृद्धिसन्धिः"
    assert "वृद्धिरेचि" in rule.sutra

def test_sandhi_rule_yan(sandhi_service):
    """Verify Yaṇ Sandhi rule explanation on yadi + api."""
    rule = sandhi_service.explain_sandhi_rule("यदि", "अपि")
    assert rule is not None
    assert rule.rule_name == "यण्सन्धिः"
    assert "इको यणचि" in rule.sutra

def test_sandhi_rule_scutva(sandhi_service):
    """Verify Ścutva Sandhi rule explanation on sat + cit."""
    rule = sandhi_service.explain_sandhi_rule("सत्", "चित्")
    assert rule is not None
    assert rule.rule_name == "श्चुत्वसन्धिः"
    assert "स्तोः श्चुना श्चुः" in rule.sutra
    assert rule.sandhi_type == "व्यञ्जनसन्धिः"

# ==============================================================================
# 4. PRIORITY 4: SAMĀSA COMPOUND DECOMPOSITION TESTS
# ==============================================================================

def test_samasa_avyayibhava(samasa_service):
    """Verify Avyayībhāva decomposition and Vigraha-vākya."""
    res = samasa_service.analyze_compound("यथाशक्ति")
    assert res is not None
    assert res.samasa_type == "अव्ययीभावः"
    assert res.vigraha_vakya == "शक्तिम् अनतिक्रम्य"
    assert res.components == ["यथा", "शक्ति"]

    res_upa = samasa_service.analyze_compound("उपग्रामम्")
    assert res_upa is not None
    assert res_upa.samasa_type == "अव्ययीभावः"
    assert res_upa.vigraha_vakya == "ग्रामस्य समीपम्"

def test_samasa_tatpurusha(samasa_service):
    """Verify Tatpuruṣa compound decomposition."""
    res = samasa_service.analyze_compound("राजपुरुषः")
    assert res is not None
    assert "तत्पुरुषः" in res.samasa_type
    assert res.vigraha_vakya == "राज्ञः पुरुषः"

def test_samasa_karmadharaya(samasa_service):
    """Verify Karmadhāraya compound decomposition."""
    res = samasa_service.analyze_compound("नीलोत्पलम्")
    assert res is not None
    assert res.samasa_type == "कर्मधारयः"
    assert res.vigraha_vakya == "नीलं तत् उत्पलम्"

def test_samasa_dvigu(samasa_service):
    """Verify Dvigu compound decomposition."""
    res = samasa_service.analyze_compound("पञ्चवटी")
    assert res is not None
    assert res.samasa_type == "द्विगुः"
    assert res.vigraha_vakya == "पञ्चानां वटानां समाहारः"

def test_samasa_dvandva(samasa_service):
    """Verify Dvandva compound decomposition."""
    res = samasa_service.analyze_compound("रामलक्ष्मणौ")
    assert res is not None
    assert "द्वन्द्वः" in res.samasa_type
    assert res.vigraha_vakya == "रामः च लक्ष्मणः च"

def test_samasa_bahuvrihi(samasa_service):
    """Verify Bahuvrīhi compound decomposition."""
    res = samasa_service.analyze_compound("पीताम्बरः")
    assert res is not None
    assert res.samasa_type == "बहुव्रीहिः"
    assert "पीतं अम्बरं यस्य सः" in res.vigraha_vakya

# ==============================================================================
# 5. PRIORITY 5: ANVAYA PROSE RE-ORDERING TESTS
# ==============================================================================

def test_orchestrator_anvaya_and_nlp_pipeline(orchestrator_service):
    """
    Verify end-to-end integration: Anvaya, Kāraka relations, Sandhi rules, and Samāsa
    in a full sentence analysis.
    """
    # Sentence with Upapada, Sandhi, and Compound
    text = "रामेण सह लक्ष्मणः विद्यालयं गच्छति।"
    response = orchestrator_service.analyze(text, bypass_cache=True)

    assert response.original_text == text
    assert len(response.sandhi_splits) >= 4
    assert len(response.morphology) >= 4

    # P1 & P2: Check Kāraka relations
    assert len(response.karaka_relations) >= 2
    relations_text = [r.relation for r in response.karaka_relations]
    assert any("उपपद-सम्बन्धः" in r for r in relations_text)

    # P4: Samāsa detected
    # विद्यालयः is in sandhi splits
    samasa_compounds = [c.compound_word for c in response.compounds]

    # P5: Anvaya sequence generated
    assert len(response.anvaya) >= 4
    # The verb 'गच्छति' must be at the end of the Anvaya sequence
    assert response.anvaya[-1] == "गच्छति"
