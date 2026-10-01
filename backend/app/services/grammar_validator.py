import logging
import re
from typing import List, Optional, Tuple, Dict, Any

from app.models.schemas import WordAnalysis, KarakaRelation, GrammarIssue

logger = logging.getLogger(__name__)

class GrammarValidator:
    """
    Pedagogical Grammar Validation Engine (दोष-परीक्षक) for CBSE/NCERT Sanskrit.
    
    Validates student sentence composition against formal Paninian grammatical concord:
    1. Subject-Verb Person Agreement (पुरुष-अन्वयः)
    2. Subject-Verb Number Agreement (वचन-अन्वयः)
    3. Adjective-Noun Concordance (विशेषण-विशेष्य-अन्वयः)
    4. Upapada-Vibhakti Constraints (उपपद-विभक्ति-परीक्षा)
    5. Incomplete Sentence Detection (समापिका क्रिया-अभावः)
    """

    # Upapada governance rules: keyword -> required case (English substring, Sanskrit label, Paninian rule)
    UPAPADA_REQUIREMENTS: Dict[str, Dict[str, Any]] = {
        "नमः": {
            "case_en": "Dative",
            "case_skt": "चतुर्थी विभक्तिः",
            "rule": "नमःस्वस्तिस्वाहास्वधाऽलंवषड्योगाच्च (२.३.१६)",
            "direction": "prev",
            "example": "देवाय नमः / गुरवे नमः",
        },
        "स्वस्ति": {
            "case_en": "Dative",
            "case_skt": "चतुर्थी विभक्तिः",
            "rule": "नमःस्वस्तिस्वाहा... (२.३.१६)",
            "direction": "prev",
            "example": "प्रजाभ्यः स्वस्ति",
        },
        "सह": {
            "case_en": "Instrumental",
            "case_skt": "तृतीया विभक्तिः",
            "rule": "सहयुक्तेऽप्रधाने (२.३.१९)",
            "direction": "prev",
            "example": "मित्रेण सह / जनकेन सह",
        },
        "साकम्": {
            "case_en": "Instrumental",
            "case_skt": "तृतीया विभक्तिः",
            "rule": "सहयुक्तेऽप्रधाने (२.३.१९)",
            "direction": "prev",
            "example": "मित्रेण साकम्",
        },
        "प्रति": {
            "case_en": "Accusative",
            "case_skt": "द्वितीया विभक्तिः",
            "rule": "अभितःपरितःसमयानिकषाहाप्रतियोगेऽपि (वार्तिकम्)",
            "direction": "prev",
            "example": "विद्यालयं प्रति",
        },
        "उभयतः": {
            "case_en": "Accusative",
            "case_skt": "द्वितीया विभक्तिः",
            "rule": "अभितःपरितः... (वार्तिकम्)",
            "direction": "both",
            "example": "ग्रामम् उभयतः",
        },
        "परितः": {
            "case_en": "Accusative",
            "case_skt": "द्वितीया विभक्तिः",
            "rule": "अभितःपरितः... (वार्तिकम्)",
            "direction": "both",
            "example": "नगरं परितः",
        },
        "बहिः": {
            "case_en": "Ablative",
            "case_skt": "पञ्चमी विभक्तिः",
            "rule": "अपादाने पञ्चमी (२.३.२८)",
            "direction": "prev",
            "example": "गृहात् बहिः / वनात् बहिः",
        },
    }

    @staticmethod
    def _extract_number_canonical(number_str: Optional[str]) -> Optional[str]:
        if not number_str:
            return None
        if "Singular" in number_str or "एकवचनम्" in number_str:
            return "Singular"
        if "Dual" in number_str or "द्विवचनम्" in number_str:
            return "Dual"
        if "Plural" in number_str or "बहुवचनम्" in number_str:
            return "Plural"
        return None

    @staticmethod
    def _extract_person_canonical(person_str: Optional[str]) -> Optional[str]:
        if not person_str:
            return None
        if "First Person" in person_str or "उत्तमपुरुषः" in person_str:
            return "First"
        if "Second Person" in person_str or "मध्यमपुरुषः" in person_str:
            return "Second"
        if "Third Person" in person_str or "प्रथमपुरुषः" in person_str:
            return "Third"
        return None

    @classmethod
    def validate(
        cls,
        morph_analyses: List[WordAnalysis],
        karaka_relations: List[KarakaRelation],
        raw_text: str = ""
    ) -> List[GrammarIssue]:
        """
        Runs comprehensive pedagogical syntax validation across the analyzed sentence.
        Returns a list of structured GrammarIssue warnings and correction hints.
        """
        issues: List[GrammarIssue] = []
        if not morph_analyses:
            return issues

        # ----------------------------------------------------------------------
        # 1. Locate Subject(s) and Finite Verb(s)
        # ----------------------------------------------------------------------
        subject_word: Optional[WordAnalysis] = None
        finite_verb: Optional[WordAnalysis] = None

        for w in morph_analyses:
            clean = w.word.strip("।,॥.?!")
            g = w.primary_gloss
            case_str = g.case or ""

            # Detect Kartā (Subject)
            if not subject_word:
                if w.karaka_role and "कर्ता" in w.karaka_role and "Relative" not in w.karaka_role:
                    subject_word = w
                elif "Nominative" in case_str and not w.is_compound and clean not in ["यः", "या", "यत्"]:
                    subject_word = w

            # Detect main finite verb (तिङन्त क्रियापदम्)
            if not finite_verb:
                if g.pos.startswith("Verb") and g.tense and g.person:
                    finite_verb = w

        # ----------------------------------------------------------------------
        # 2. Check Subject-Verb Person & Number Agreement (पुरुष-वचन अन्वयः)
        # ----------------------------------------------------------------------
        if subject_word and finite_verb:
            subj_clean = subject_word.word.strip("।,॥.?!")
            verb_clean = finite_verb.word.strip("।,॥.?!")
            s_gloss = subject_word.primary_gloss
            v_gloss = finite_verb.primary_gloss

            # 2.1 Person Agreement (पुरुष-अन्वयः)
            expected_person = "Third"
            if s_gloss.root == "अस्मद्" or subj_clean in ["अहम्", "अहं", "आवाम्", "वयम्"]:
                expected_person = "First"
            elif s_gloss.root == "युष्मद्" or subj_clean in ["त्वम्", "त्वं", "युवाम्", "यूयम्"]:
                expected_person = "Second"

            actual_verb_person = cls._extract_person_canonical(v_gloss.person)

            if actual_verb_person and actual_verb_person != expected_person:
                person_names_skt = {
                    "First": "उत्तमपुरुषः (First Person)",
                    "Second": "मध्यमपुरुषः (Second Person)",
                    "Third": "प्रथमपुरुषः (Third Person)",
                }
                issues.append(
                    GrammarIssue(
                        issue_type="SUBJECT_VERB_PERSON_MISMATCH",
                        severity="error",
                        erroneous_token=f"{subj_clean} ... {verb_clean}",
                        sanskrit_explanation=(
                            f"कर्तृ-क्रिया पुरुष-असंगतिः: कर्ता '{subj_clean}' कृते "
                            f"{person_names_skt[expected_person]} अपेक्षितम् अस्ति, "
                            f"किन्तु क्रियापदम् '{verb_clean}' {person_names_skt.get(actual_verb_person, '')} मध्ये अस्ति।"
                        ),
                        english_explanation=(
                            f"Subject-Verb Person Mismatch: The subject '{subj_clean}' requires a "
                            f"{expected_person}-person verb ending, but found {actual_verb_person}-person '{verb_clean}'."
                        ),
                        suggested_correction=(
                            f"Replace '{verb_clean}' with matching {expected_person}-person conjugation for '{subj_clean}'."
                        ),
                    )
                )

            # 2.2 Number Agreement (वचन-अन्वयः)
            subj_num = cls._extract_number_canonical(s_gloss.number)
            verb_num = cls._extract_number_canonical(v_gloss.number)

            if subj_num and verb_num and subj_num != verb_num:
                vacana_names_skt = {
                    "Singular": "एकवचनम् (Singular)",
                    "Dual": "द्विवचनम् (Dual)",
                    "Plural": "बहुवचनम् (Plural)",
                }
                issues.append(
                    GrammarIssue(
                        issue_type="SUBJECT_VERB_NUMBER_MISMATCH",
                        severity="error",
                        erroneous_token=f"{subj_clean} ... {verb_clean}",
                        sanskrit_explanation=(
                            f"कर्तृ-क्रिया वचन-असंगतिः: कर्ता '{subj_clean}' {vacana_names_skt[subj_num]} अस्ति, "
                            f"अतः क्रियापदम् अपि {vacana_names_skt[subj_num]} भवेत् (न तु {vacana_names_skt[verb_num]})।"
                        ),
                        english_explanation=(
                            f"Subject-Verb Number Mismatch: Subject '{subj_clean}' is {subj_num}, "
                            f"which requires a {subj_num} verb, but '{verb_clean}' is {verb_num}."
                        ),
                        suggested_correction=(
                            f"Change verb '{verb_clean}' to {subj_num} number matching subject '{subj_clean}'."
                        ),
                    )
                )

        # ----------------------------------------------------------------------
        # 3. Check Adjective-Noun Concordance (विशेषण-विशेष्य अन्वयः)
        # ----------------------------------------------------------------------
        COMMON_ADJECTIVES = {
            "विशाल", "सुन्दर", "श्रेष्ठ", "मधुर", "तीक्ष्ण", "महत्", "महान्", "चतुर", "कुशल",
            "दीर्घ", "लघु", "रक्त", "श्वेत", "कृष्ण", "पीत", "शुभ्र", "नव", "पुरातन", "उत्तम",
            "दुष्ट", "सज्जन", "प्रिय", "शूर", "वीर", "पाप", "पुण्य"
        }
        for i in range(len(morph_analyses) - 1):
            w1 = morph_analyses[i]
            w2 = morph_analyses[i + 1]
            c1 = w1.word.strip("।,॥.?!")
            c2 = w2.word.strip("।,॥.?!")
            g1 = w1.primary_gloss
            g2 = w2.primary_gloss

            # Check if w1 is an adjective or qualifier before noun w2
            is_adj = (w1.karaka_role and "विशेषणम्" in w1.karaka_role) or (g1.root in COMMON_ADJECTIVES)
            is_noun_head = (w2.karaka_role and "कर्ता" in w2.karaka_role) or (g2.pos.startswith("Noun") and not w2.is_compound)

            if is_adj and is_noun_head:
                case1 = g1.case or ""
                case2 = g2.case or ""
                has_case_mismatch = case1 and case2 and not any(k in case1 and k in case2 for k in ["Nominative", "Accusative", "Instrumental", "Dative", "Ablative", "Genitive", "Locative"])
                has_gender_mismatch = g1.gender and g2.gender and (g1.gender.split(" / ")[0] != g2.gender.split(" / ")[0]) and ("Nominative" in case2)

                if has_case_mismatch or has_gender_mismatch:
                    issues.append(
                        GrammarIssue(
                            issue_type="ADJECTIVE_NOUN_CONCORDANCE_ERROR",
                            severity="warning",
                            erroneous_token=f"{c1} {c2}",
                            sanskrit_explanation=(
                                f"विशेषण-विशेष्य विभक्ति/लिङ्ग-भेदः: विशेषणम् '{c1}' तथा विशेष्यम् '{c2}' "
                                f"समाने लिङ्गे विभक्तौ च भवेताम् (यल्लिङ्गं यद्वचनं या च विभक्तिर्विशेषणस्य, तल्लिङ्गं तद्वचनं सा च विभक्तिर्विशेष्यस्यपि)।"
                            ),
                            english_explanation=(
                                f"Adjective-Noun Concordance Mismatch: The adjective '{c1}' must match the grammatical case and gender "
                                f"of the noun '{c2}'."
                            ),
                            suggested_correction=f"Decline adjective '{c1}' in the same case and gender as '{c2}'.",
                        )
                    )

        # ----------------------------------------------------------------------
        # 4. Check Upapada-Vibhakti Violations (उपपद-विभक्ति-दोषः)
        # ----------------------------------------------------------------------
        token_list = [w.word.strip("।,॥.?!") for w in morph_analyses]
        for idx, token in enumerate(token_list):
            if token in cls.UPAPADA_REQUIREMENTS:
                req = cls.UPAPADA_REQUIREMENTS[token]
                req_case_en = req["case_en"]
                req_case_skt = req["case_skt"]

                # Target is usually immediately preceding word
                target_idx = None
                if req["direction"] in ["prev", "both"] and idx > 0:
                    target_idx = idx - 1
                elif req["direction"] in ["next", "both"] and idx < len(morph_analyses) - 1:
                    target_idx = idx + 1

                if target_idx is not None:
                    target_word = morph_analyses[target_idx]
                    t_clean = target_word.word.strip("।,॥.?!")
                    t_case = target_word.primary_gloss.case or ""

                    # Verify if the target word has the required case
                    has_required_case = req_case_en in t_case
                    if not has_required_case:
                        # Also check alternative glosses before raising error
                        if not any(req_case_en in (alt.case or "") for alt in target_word.alternative_glosses):
                            issues.append(
                                GrammarIssue(
                                    issue_type="UPAPADA_CASE_VIOLATION",
                                    severity="error",
                                    erroneous_token=f"{t_clean} {token}",
                                    sanskrit_explanation=(
                                        f"उपपद-विभक्ति-दोषः: '{token}' पदस्य योगे {req_case_skt} अपेक्षिता भवति "
                                        f"({req['rule']}), किन्तु '{t_clean}' इति पदे सा न दृश्यते। उदाहरणम्: {req['example']}।"
                                    ),
                                    english_explanation=(
                                        f"Upapada Case Violation: The governing particle '{token}' strictly requires "
                                        f"{req_case_en} case ({req_case_skt}), but '{t_clean}' is not declined in {req_case_en}. "
                                        f"Standard pattern: {req['example']}."
                                    ),
                                    suggested_correction=f"Decline '{t_clean}' in {req_case_skt} before '{token}'.",
                                )
                            )

        # ----------------------------------------------------------------------
        # 5. Incomplete Sentence Detection (समापिका क्रिया-अभावः)
        # ----------------------------------------------------------------------
        words_count = len([w for w in morph_analyses if w.word.strip("।,॥.?!")])
        if words_count >= 3 and not finite_verb:
            # Check if sentence has participles without a concluding copula
            has_participle = any(
                w.primary_gloss.pos.startswith("Participle") or w.primary_gloss.pratyaya
                for w in morph_analyses
            )
            issues.append(
                GrammarIssue(
                    issue_type="MISSING_FINITE_VERB",
                    severity="suggestion",
                    erroneous_token=raw_text.strip("।,॥.?!"),
                    sanskrit_explanation=(
                        "वाक्ये समापिकायाः क्रियायाः (तिङन्तपदस्य) अभावः दृश्यते। "
                        "वाक्यस्य पूर्णतायै 'अस्ति', 'आसीत्', 'भवति' वा क्रियापदं योजयितुं शक्यते।"
                    ),
                    english_explanation=(
                        "The sentence appears to be missing a concluding finite verb (समापिका क्रियापदम्). "
                        "In standard Sanskrit prose, consider completing the clause with an explicit verb like 'अस्ति' or 'पठति'."
                    ),
                    suggested_correction="Add an appropriate finite verb to complete the clause.",
                )
            )

        return issues
