import pytest
from app.services.orchestrator import get_orchestrator_service

@pytest.fixture(scope="module")
def orch():
    return get_orchestrator_service()

def test_correct_sentences_have_no_errors(orch):
    """Correct textbook sentences must produce zero grammar errors."""
    for text in ["बालकः पुस्तकं पठति।", "वयं विद्यालये पठामः।", "सः सदा सत्यं वदति।", "देवाय नमः।"]:
        res = orch.analyze(text, bypass_cache=True)
        errors = [w for w in res.grammar_warnings if w.severity == "error"]
        assert len(errors) == 0, f"Expected 0 errors for '{text}', got: {errors}"

def test_subject_verb_person_mismatch_first_person(orch):
    """Detects when 1st person subject (अहम्) has a 3rd person verb (पठति)."""
    res = orch.analyze("अहं पुस्तकं पठति।", bypass_cache=True)
    mismatches = [w for w in res.grammar_warnings if w.issue_type == "SUBJECT_VERB_PERSON_MISMATCH"]
    assert len(mismatches) >= 1
    assert "अहं" in mismatches[0].erroneous_token or "अहम्" in mismatches[0].erroneous_token
    assert "First" in mismatches[0].english_explanation

def test_subject_verb_person_mismatch_second_person(orch):
    """Detects when 2nd person subject (त्वम्) has a 3rd person verb (पठति)."""
    res = orch.analyze("त्वं पुस्तकं पठति।", bypass_cache=True)
    mismatches = [w for w in res.grammar_warnings if w.issue_type == "SUBJECT_VERB_PERSON_MISMATCH"]
    assert len(mismatches) >= 1
    assert "Second" in mismatches[0].english_explanation

def test_subject_verb_number_mismatch_plural_subject(orch):
    """Detects when plural subject (बालकाः) has a singular verb (पठति)."""
    res = orch.analyze("बालकाः पुस्तकं पठति।", bypass_cache=True)
    mismatches = [w for w in res.grammar_warnings if w.issue_type == "SUBJECT_VERB_NUMBER_MISMATCH"]
    assert len(mismatches) >= 1
    assert "Plural" in mismatches[0].english_explanation or "बहुवचनम्" in mismatches[0].sanskrit_explanation

def test_subject_verb_number_mismatch_singular_subject(orch):
    """Detects when singular subject (बालकः) has a plural verb (पठन्ति)."""
    res = orch.analyze("बालकः पुस्तकं पठन्ति।", bypass_cache=True)
    mismatches = [w for w in res.grammar_warnings if w.issue_type == "SUBJECT_VERB_NUMBER_MISMATCH"]
    assert len(mismatches) >= 1
    assert "Singular" in mismatches[0].english_explanation or "एकवचनम्" in mismatches[0].sanskrit_explanation

def test_upapada_case_violation_namah(orch):
    """Detects when 'नमः' is preceded by Instrumental instead of Dative (रामेण नमः -> रामाय नमः)."""
    res = orch.analyze("रामेण नमः।", bypass_cache=True)
    violations = [w for w in res.grammar_warnings if w.issue_type == "UPAPADA_CASE_VIOLATION"]
    assert len(violations) >= 1
    assert "नमः" in violations[0].erroneous_token
    assert "Dative" in violations[0].english_explanation or "चतुर्थी" in violations[0].sanskrit_explanation

def test_upapada_case_violation_saha(orch):
    """Detects when 'सह' is preceded by Genitive instead of Instrumental (रामस्य सह -> रामेण सह)."""
    res = orch.analyze("रामस्य सह बालकः गच्छति।", bypass_cache=True)
    violations = [w for w in res.grammar_warnings if w.issue_type == "UPAPADA_CASE_VIOLATION"]
    assert len(violations) >= 1
    assert "सह" in violations[0].erroneous_token
    assert "Instrumental" in violations[0].english_explanation or "तृतीया" in violations[0].sanskrit_explanation

def test_adjective_noun_concordance_warning(orch):
    """Detects when an adjective does not match its noun in case/gender (e.g. विशालं वृक्षः)."""
    res = orch.analyze("विशालं वृक्षः अस्ति।", bypass_cache=True)
    warnings = [w for w in res.grammar_warnings if w.issue_type == "ADJECTIVE_NOUN_CONCORDANCE_ERROR"]
    assert len(warnings) >= 1
    assert "विशेषण" in warnings[0].sanskrit_explanation

def test_incomplete_sentence_suggestion(orch):
    """Suggests completing a multi-word clause missing a finite verb."""
    res = orch.analyze("एकस्मिन् वने विशालः वटवृक्षः।", bypass_cache=True)
    suggestions = [w for w in res.grammar_warnings if w.issue_type == "MISSING_FINITE_VERB"]
    assert len(suggestions) >= 1
    assert "समापिका" in suggestions[0].sanskrit_explanation or "finite verb" in suggestions[0].english_explanation
