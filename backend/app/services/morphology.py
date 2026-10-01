import re
import logging
import threading
from collections import OrderedDict
from functools import lru_cache
from typing import List, Optional, Set, Tuple, Dict, Any

from indic_transliteration import sanscript
from sanskrit_parser.base.sanskrit_base import SanskritNormalizedString
from sanskrit_parser.parser.sandhi_analyzer import LexicalSandhiAnalyzer

from app.core.normalizer import SanskritNormalizer
from app.core.modern_lexicon import MODERN_SANSKRIT_TERMS
from app.models.schemas import MorphologicalGloss, WordAnalysis, KarakaRelation

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. NCERT BILINGUAL TAG TRANSLATION TABLES
# ==============================================================================

VIBHAKTI_MAP: Dict[str, Tuple[str, str]] = {
    "praTamAviBaktiH": ("प्रथमा विभक्तिः (कर्ता)", "Nominative (1st Case)"),
    "dvitIyAviBaktiH": ("द्वितीया विभक्तिः (कर्म)", "Accusative (2nd Case)"),
    "tftIyAviBaktiH": ("तृतीया विभक्तिः (करण)", "Instrumental (3rd Case)"),
    "caturTIviBaktiH": ("चतुर्थी विभक्तिः (सम्प्रदान)", "Dative (4th Case)"),
    "paYcamIviBaktiH": ("पञ्चमी विभक्तिः (अपादान)", "Ablative (5th Case)"),
    "zazWIviBaktiH": ("षष्ठी विभक्तिः (सम्बन्ध)", "Genitive (6th Case)"),
    "saptamIviBaktiH": ("सप्तमी विभक्तिः (अधिकरण)", "Locative (7th Case)"),
    "saMboDanaviBaktiH": ("सम्बोधनम्", "Vocative (Addressing)"),
}

LINGA_MAP: Dict[str, Tuple[str, str]] = {
    "puMlliNgam": ("पुंल्लिङ्गम्", "Masculine"),
    "strIliNgam": ("स्त्रीलिङ्गम्", "Feminine"),
    "napuMsakaliNgam": ("नपुंसकलिङ्गम्", "Neuter"),
    "triliNgam": ("त्रिषु लिङ्गेषु समानम्", "All Genders"),
}

VACANA_MAP: Dict[str, Tuple[str, str]] = {
    "ekavacanam": ("एकवचनम्", "Singular"),
    "dvivacanam": ("द्विवचनम्", "Dual"),
    "bahuvacanam": ("बहुवचनम्", "Plural"),
}

LAKARA_MAP: Dict[str, Tuple[str, str]] = {
    "law": ("लट् लकारः (वर्तमानकालः)", "Present Tense (Laṭ)"),
    "laN": ("लङ् लकारः (अनद्यतनभूतकालः)", "Past Imperfect Tense (Laṅ)"),
    "lfw": ("लृट् लकारः (भविष्यत्कालः)", "Simple Future Tense (Lṛṭ)"),
    "low": ("लोट् लकारः (आज्ञार्थकः)", "Imperative Mood (Loṭ)"),
    "viDiliN": ("विधिलिङ् लकारः (विधि/प्रार्थना)", "Potential/Optative Mood (Vidhiliṅ)"),
    "liw": ("लिट् लकारः (परोक्षभूतकालः)", "Perfect Past Tense (Liṭ)"),
    "luN": ("लुङ् लकारः (सामान्यभूतकालः)", "Aorist Past Tense (Luṅ)"),
}

PURUSHA_MAP: Dict[str, Tuple[str, str]] = {
    "praTamapuruzaH": ("प्रथमपुरुषः (अन्यपुरुषः)", "Third Person (He/She/It/They)"),
    "maDyamapuruzaH": ("मध्यमपुरुषः", "Second Person (You)"),
    "uttamapuruzaH": ("उत्तमपुरुषः", "First Person (I/We)"),
}

PRATYAYA_MAP: Dict[str, Tuple[str, str]] = {
    "ktvA": ("क्त्वा प्रत्ययः", "Ktvā (having done / gerund)"),
    "lyap": ("ल्यप् प्रत्ययः", "Lyap (having done with prefix / gerund)"),
    "tumun": ("तुमुन् प्रत्ययः", "Tumun (in order to / infinitive)"),
    "Satf": ("शतृ प्रत्ययः", "Śatṛ (while doing / present active participle)"),
    "Sanac": ("शानच् प्रत्ययः", "Śānac (while doing / present middle participle)"),
    "kta": ("क्त प्रत्ययः", "Kta (past passive participle)"),
    "ktavatu": ("क्तवतु प्रत्ययः", "Ktavatu (past active participle)"),
    "tavya": ("तव्यत् प्रत्ययः", "Tavyat (should be done / obligative)"),
    "tavyat": ("तव्यत् प्रत्ययः", "Tavyat (should be done / obligative)"),
    "anIya": ("अनीयर प्रत्ययः", "Anīyar (should be done / obligative)"),
    "anIyar": ("अनीयर प्रत्ययः", "Anīyar (should be done / obligative)"),
    "yat": ("यत् प्रत्ययः", "Yat (should be done)"),
    "kftya": ("कृत्य प्रत्ययः", "Kṛtya (obligative participle)"),
    "matup": ("मतुप् प्रत्ययः", "Matup (possessive suffix)"),
    "Wak": ("ठक् प्रत्ययः", "Ṭhak (derivational suffix -ika / 'सम्बन्धी')"),
    "tva": ("त्व प्रत्ययः", "Tva (abstract noun suffix)"),
    "tal": ("तल् प्रत्ययः", "Tal (abstract noun suffix)"),
}

PRAYOGA_MAP: Dict[str, Tuple[str, str]] = {
    "kartari": ("कर्तरि प्रयोगः", "Active Voice"),
    "karmaNi": ("कर्मणि प्रयोगः", "Passive Voice"),
    "karmaRi": ("कर्मणि प्रयोगः", "Passive Voice"),
    "BAve": ("भावे प्रयोगः", "Impersonal Voice"),
    "Bave": ("भावे प्रयोगः", "Impersonal Voice"),
}

PADA_MAP: Dict[str, Tuple[str, str]] = {
    "parasmEpadam": ("परस्मैपदम्", "Parasmaipada (Active)"),
    "Atmanepadam": ("आत्मनेपदम्", "Atmanepada (Middle)"),
    "uBayapadam": ("उभयपदम्", "Ubhayapada (Dual)"),
}

# The 22 Classical Sanskrit Upasargas (Prefixes) mapped from SLP1 to Devanagari.
# Ordered by length descending so multi-syllable prefixes match first.
UPASARGAS_MAPPING: List[Tuple[str, str]] = [
    ("prati", "प्रति"),
    ("parA", "परा"),
    ("pari", "परि"),
    ("aBi", "अभि"),
    ("aDi", "अधि"),
    ("ati", "अति"),
    ("api", "अपि"),
    ("anu", "अनु"),
    ("apa", "अप"),
    ("ava", "अव"),
    ("upa", "उप"),
    ("nis", "निस्"),
    ("nir", "निर्"),
    ("dus", "दुस्"),
    ("dur", "दुर्"),
    ("sam", "सम्"),
    ("saM", "सं"),
    ("pra", "प्र"),
    ("vi", "वि"),
    ("ni", "नि"),
    ("su", "सु"),
    ("ud", "उद्"),
    ("ut", "उत्"),
    ("A", "आ"),
]
UPASARGAS_MAPPING.sort(key=lambda x: len(x[0]), reverse=True)

UPASARGAS: List[str] = [
    "प्र", "परा", "अप", "सम्", "सं", "अनु", "अव", "निस्", "निर्", "दुस्", "दुर्",
    "वि", "आ", "नि", "अधि", "अपि", "अति", "सु", "उद्", "उत्", "अभि", "प्रति",
    "परि", "उप"
]

# ==============================================================================
# 2. CURATED CBSE / NCERT AVYAYA (अव्यय) LEXICON
# ==============================================================================

NCERT_AVYAYAS: Dict[str, Tuple[str, str]] = {
    "अपि": ("अपि", "also / even"),
    "च": ("च", "and"),
    "अत्र": ("अत्र", "here"),
    "तत्र": ("तत्र", "there"),
    "कुत्र": ("कुत्र", "where"),
    "कदा": ("कदा", "when"),
    "तदा": ("तदा", "then"),
    "यदा": ("यदा", "whenever / when"),
    "सदा": ("सदा", "always"),
    "सर्वदा": ("सर्वदा", "always / at all times"),
    "यथा": ("यथा", "just as / as"),
    "तथा": ("तथा", "similarly / so"),
    "एव": ("एव", "only / indeed / alone"),
    "विना": ("विना", "without"),
    "सह": ("सह", "with / together with"),
    "यदि": ("यदि", "if"),
    "तर्हि": ("तर्हि", "then"),
    "इति": ("इति", "thus / indicating direct speech"),
    "अद्य": ("अद्य", "today"),
    "श्वः": ("श्वः", "tomorrow"),
    "ह्यः": ("ह्यः", "yesterday"),
    "अलम्": ("अलम्", "enough / do not"),
    "प्रातः": ("प्रातः", "in the morning"),
    "सायम्": ("सायम्", "in the evening"),
    "शनैः": ("शनैः", "slowly"),
    "उच्चैः": ("उच्चैः", "loudly / high"),
    "नीचैः": ("नीचैः", "softly / low"),
    "पुनः": ("पुनः", "again"),
    "मा": ("मा", "do not (prohibitive)"),
    "न": ("न", "not / no"),
    "किम्": ("किम्", "what / why"),
    "कथम्": ("कथम्", "how"),
    "इदानीम्": ("इदानीम्", "now / at this moment"),
    "अधुना": ("अधुना", "now / currently"),
    "सम्प्रति": ("सम्प्रति", "nowadays / presently"),
    "बहिः": ("बहिः", "outside"),
    "अन्तः": ("अन्तः", "inside"),
    "उपरि": ("उपरि", "above / over"),
    "अधः": ("अधः", "below / underneath"),
    "सर्वत्र": ("सर्वत्र", "everywhere"),
    "एकत्र": ("एकत्र", "in one place / together"),
    "एकदा": ("एकदा", "once / at one time"),
    "सहसा": ("सहसा", "suddenly / unexpectedly"),
    "वृथा": ("वृथा", "in vain / uselessly"),
    "मुहुर्मुहुः": ("मुहुर्मुहुः", "again and again / repeatedly"),
    "पुरा": ("पुरा", "formerly / in ancient times"),
    "परश्वः": ("परश्वः", "day after tomorrow"),
    "प्रह्यः": ("प्रह्यः", "day before yesterday"),
    "कदापि": ("कदापि", "ever / at any time"),
    "नहि": ("नहि", "surely not / by no means"),
    "नूनम्": ("नूनम्", "certainly / definitely"),
}

# ==============================================================================
# 2.1 CBSE / NCERT UPAPADA-VIBHAKTI (उपपद-विभक्तयः) GOVERNING RULES
# ==============================================================================

UPAPADA_GOVERNORS: Dict[str, Dict[str, Any]] = {
    # तृतीया (3rd Case / Instrumental)
    "सह": {
        "vibhakti": "तृतीया",
        "case_en": "Instrumental",
        "direction": "prev",
        "rule": "सहयुक्तेऽप्रधाने (२.३.१९)",
        "meaning": "with / along with",
    },
    "साकम्": {
        "vibhakti": "तृतीया",
        "case_en": "Instrumental",
        "direction": "prev",
        "rule": "सहयुक्तेऽप्रधाने (२.३.१९)",
        "meaning": "along with",
    },
    "सार्धम्": {
        "vibhakti": "तृतीया",
        "case_en": "Instrumental",
        "direction": "prev",
        "rule": "सहयुक्तेऽप्रधाने (२.३.१९)",
        "meaning": "along with",
    },
    "समम्": {
        "vibhakti": "तृतीया",
        "case_en": "Instrumental",
        "direction": "prev",
        "rule": "सहयुक्तेऽप्रधाने (२.३.१९)",
        "meaning": "together with",
    },
    "विना": {
        "vibhakti": "तृतीया",
        "case_en": "Instrumental",
        "direction": "both",
        "rule": "पृथग्विनानानाभिस्तृतीयान्यतरस्याम् (२.३.३२)",
        "allowed_cases": ["Instrumental", "Accusative", "Ablative", "तृतीया", "द्वितीया", "पञ्चमी"],
        "meaning": "without",
    },
    "अलम्": {
        "vibhakti": "तृतीया",
        "case_en": "Instrumental",
        "direction": "next",
        "rule": "अलं विवादेन (निषेधार्थे तृतीया)",
        "allowed_cases": ["Instrumental", "Dative", "तृतीया", "चतुर्थी"],
        "meaning": "enough / prohibitive",
    },
    # अङ्गविकारः (Body defect / 3rd Case)
    "काणः": {
        "vibhakti": "तृतीया",
        "case_en": "Instrumental",
        "direction": "prev",
        "rule": "येनाङ्गविकारः (२.३.२०)",
        "meaning": "blind in (eye)",
    },
    "खञ्जः": {
        "vibhakti": "तृतीया",
        "case_en": "Instrumental",
        "direction": "prev",
        "rule": "येनाङ्गविकारः (२.३.२०)",
        "meaning": "lame in (leg)",
    },
    "बधिरः": {
        "vibhakti": "तृतीया",
        "case_en": "Instrumental",
        "direction": "prev",
        "rule": "येनाङ्गविकारः (२.३.२०)",
        "meaning": "deaf in (ear)",
    },
    # चतुर्थी (4th Case / Dative)
    "नमः": {
        "vibhakti": "चतुर्थी",
        "case_en": "Dative",
        "direction": "prev",
        "rule": "नमःस्वस्तिस्वाहास्वधाऽलंवषड्योगाच्च (२.३.१६)",
        "meaning": "salutations / obeisance to",
    },
    "स्वस्ति": {
        "vibhakti": "चतुर्थी",
        "case_en": "Dative",
        "direction": "prev",
        "rule": "नमःस्वस्तिस्वाहा... (२.३.१६)",
        "meaning": "wellbeing / auspiciousness to",
    },
    "स्वाहा": {
        "vibhakti": "चतुर्थी",
        "case_en": "Dative",
        "direction": "prev",
        "rule": "नमःस्वस्तिस्वाहा... (२.३.१६)",
        "meaning": "sacrificial oblations to",
    },
    "स्वधा": {
        "vibhakti": "चतुर्थी",
        "case_en": "Dative",
        "direction": "prev",
        "rule": "नमःस्वस्तिस्वाहा... (२.३.१६)",
        "meaning": "ancestral offerings to",
    },
    "रोचते": {
        "vibhakti": "चतुर्थी",
        "case_en": "Dative",
        "direction": "prev",
        "rule": "रुच्यर्थानां प्रीयमाणः (१.४.३३)",
        "meaning": "pleases / liked by",
    },
    "क्रुध्यति": {
        "vibhakti": "चतुर्थी",
        "case_en": "Dative",
        "direction": "prev",
        "rule": "क्रुधद्रुहेर्ष्यासूयार्थानां यं प्रति कोपः (१.४.३७)",
        "meaning": "is angry towards",
    },
    "कुप्यति": {
        "vibhakti": "चतुर्थी",
        "case_en": "Dative",
        "direction": "prev",
        "rule": "क्रुधद्रुहेर्ष्यासूयार्थानां यं प्रति कोपः (१.४.३७)",
        "meaning": "is angry with",
    },
    "यच्छति": {
        "vibhakti": "चतुर्थी",
        "case_en": "Dative",
        "direction": "prev",
        "rule": "दाणश्च सा चेच्चतुर्थ्यर्थे (१.४.३२)",
        "meaning": "gives to",
    },
    "ददाति": {
        "vibhakti": "चतुर्थी",
        "case_en": "Dative",
        "direction": "prev",
        "rule": "दाणश्च सा चेच्चतुर्थ्यर्थे (१.४.३२)",
        "meaning": "gives to",
    },
    # द्वितीया (2nd Case / Accusative)
    "प्रति": {
        "vibhakti": "द्वितीया",
        "case_en": "Accusative",
        "direction": "prev",
        "rule": "लक्षणेत्थंभूताख्यानभागवीप्सासु प्रतिपर्यन्ववः (१.४.९०)",
        "meaning": "towards / in direction of",
    },
    "परितः": {
        "vibhakti": "द्वितीया",
        "case_en": "Accusative",
        "direction": "prev",
        "rule": "उभयसर्वतसोः कार्या धिगुपर्यादिषु त्रिषु (द्वितीया)",
        "meaning": "all around",
    },
    "उभयतः": {
        "vibhakti": "द्वितीया",
        "case_en": "Accusative",
        "direction": "prev",
        "rule": "उभयसर्वतसोः कार्या... (द्वितीया)",
        "meaning": "on both sides of",
    },
    "सर्वतः": {
        "vibhakti": "द्वितीया",
        "case_en": "Accusative",
        "direction": "prev",
        "rule": "उभयसर्वतसोः कार्या... (द्वितीया)",
        "meaning": "on all sides of",
    },
    "धिक्": {
        "vibhakti": "द्वितीया",
        "case_en": "Accusative",
        "direction": "next",
        "rule": "धिक्योगे द्वितीया",
        "meaning": "shame upon / censure",
    },
    "अन्तरा": {
        "vibhakti": "द्वितीया",
        "case_en": "Accusative",
        "direction": "both",
        "rule": "अन्तराऽन्तरेण युक्ते (२.३.४)",
        "meaning": "between / without",
    },
    "अन्तरेण": {
        "vibhakti": "द्वितीया",
        "case_en": "Accusative",
        "direction": "both",
        "rule": "अन्तराऽन्तरेण युक्ते (२.३.४)",
        "meaning": "without / concerning",
    },
    # पञ्चमी (5th Case / Ablative)
    "बहिः": {
        "vibhakti": "पञ्चमी",
        "case_en": "Ablative",
        "direction": "prev",
        "rule": "अपादाने पञ्चमी (बहिर्योगे)",
        "meaning": "outside of",
    },
    "ऋते": {
        "vibhakti": "पञ्चमी",
        "case_en": "Ablative",
        "direction": "both",
        "rule": "अन्यारादितरर्तेदिक्शब्दाञ्चूत्तरपदाजाहियुक्ते (२.३.२९)",
        "meaning": "except / without",
    },
    "बिभेति": {
        "vibhakti": "पञ्चमी",
        "case_en": "Ablative",
        "direction": "prev",
        "rule": "भीत्रार्थानां भयहेतुः (१.४.२५)",
        "meaning": "fears from",
    },
    "भीतः": {
        "vibhakti": "पञ्चमी",
        "case_en": "Ablative",
        "direction": "prev",
        "rule": "भीत्रार्थानां भयहेतुः (१.४.२५)",
        "meaning": "frightened of",
    },
    "रक्षति": {
        "vibhakti": "पञ्चमी",
        "case_en": "Ablative",
        "direction": "prev",
        "rule": "त्राणार्थानां रक्षणे पञ्चमी",
        "meaning": "protects from",
    },
    "प्रभवति": {
        "vibhakti": "पञ्चमी",
        "case_en": "Ablative",
        "direction": "prev",
        "rule": "भुवः प्रभवः (१.४.३१)",
        "meaning": "originates from",
    },
    # षष्ठी (6th Case / Genitive)
    "पुरतः": {
        "vibhakti": "षष्ठी",
        "case_en": "Genitive",
        "direction": "prev",
        "rule": "सम्बन्धे षष्ठी (पुरतोयोगे)",
        "meaning": "in front of",
    },
    "पृष्ठतः": {
        "vibhakti": "षष्ठी",
        "case_en": "Genitive",
        "direction": "prev",
        "rule": "सम्बन्धे षष्ठी (पृष्ठतोयोगे)",
        "meaning": "behind",
    },
    "उपरि": {
        "vibhakti": "षष्ठी",
        "case_en": "Genitive",
        "direction": "prev",
        "rule": "षष्ठ्यतसर्थप्रत्ययेन (२.३.३०)",
        "meaning": "above / upon",
    },
    "अधः": {
        "vibhakti": "षष्ठी",
        "case_en": "Genitive",
        "direction": "prev",
        "rule": "अधोयोगे षष्ठी",
        "meaning": "underneath",
    },
    # सप्तमी (7th Case / Locative)
    "कुशलः": {
        "vibhakti": "सप्तमी",
        "case_en": "Locative",
        "direction": "prev",
        "rule": "सप्तमी शौण्डैः (२.१.४०)",
        "meaning": "skilled in",
    },
    "निपुणः": {
        "vibhakti": "सप्तमी",
        "case_en": "Locative",
        "direction": "prev",
        "rule": "सप्तमी शौण्डैः (२.१.४०)",
        "meaning": "expert in",
    },
    "प्रवीणः": {
        "vibhakti": "सप्तमी",
        "case_en": "Locative",
        "direction": "prev",
        "rule": "सप्तमी शौण्डैः (२.१.४०)",
        "meaning": "proficient in",
    },
    "पटुः": {
        "vibhakti": "सप्तमी",
        "case_en": "Locative",
        "direction": "prev",
        "rule": "सप्तमी शौण्डैः (२.१.४०)",
        "meaning": "clever in",
    },
    "स्निह्यति": {
        "vibhakti": "सप्तमी",
        "case_en": "Locative",
        "direction": "prev",
        "rule": "स्नेहार्थे सप्तमी",
        "meaning": "has affection for",
    },
}

# ==============================================================================
# 3. CANONICAL DHĀTU MAPPING & FALLBACK PATTERNS
# ==============================================================================

# Mapping inflected verb/participle stems to their Paninian lexical root
DHATU_CANONICAL: Dict[str, str] = {
    "गच्छ": "गम्", "गमि": "गम्", "गन्तु": "गम्", "गत": "गम्", "गतवत्": "गम्",
    "पश्य": "दृश्", "द्रक्ष्य": "दृश्", "द्रष्टु": "दृश्", "दृष्ट": "दृश्",
    "पिब": "पा", "पास्य": "पा", "पातु": "पा", "पीत": "पा",
    "तिष्ठ": "स्था", "स्थास्य": "स्था", "स्थातु": "स्था", "स्थित": "स्था",
    "भव": "भू", "भविष्य": "भू", "भवितु": "भू", "भूत": "भू",
    "कुरु": "कृ", "करो": "कृ", "करिष्य": "कृ", "कर्तु": "कृ", "कृत": "कृ", "कृतवत्": "कृ",
    "नय": "नी", "नेष्य": "नी", "नेतु": "नी", "नीत": "नी",
    "हर": "हृ", "हरिष्य": "हृ", "हर्तु": "हृ", "हृत": "हृ",
    "स्मर": "स्मृ", "स्मरिष्य": "स्मृ", "स्मर्तु": "स्मृ", "स्मृत": "स्मृ",
    "पठ": "पठ्", "पठिष्य": "पठ्", "पठितु": "पठ्", "पठित": "पठ्", "पठितवत्": "पठ्",
    "लिख": "लिख्", "लेखिष्य": "लिख्", "लेखितु": "लिख्", "लिखित": "लिख्",
    "वद": "वद्", "वदिष्य": "वद्", "वदितु": "वद्", "उदित": "वद्",
    "खाद": "खाद्", "खादिष्य": "खाद्", "खादितु": "खाद्", "खादित": "खाद्",
    "हस": "हस्", "हसिष्य": "हस्", "हसितु": "हस्", "हसित": "हस्",
    "धाव": "धाव्", "धाविष्य": "धाव्", "धावितु": "धाव्", "धावित": "धाव्",
    "नम": "नम्", "णम": "नम्", "नंस्य": "नम्", "नन्तु": "नम्", "नत": "नम्",
    "जीव": "जीव्", "जीव": "जीव्",
    "ज्ञा": "ज्ञा", "जाना": "ज्ञा", "ज्ञातु": "ज्ञा", "ज्ञात": "ज्ञा",
    "शृणु": "श्रु", "श्रोष्य": "श्रु", "श्रोतु": "श्रु", "श्रुत": "श्रु",
    # Classical & Ātmanepada verbs
    "रोच": "रुच्", "रुच्य": "रुच्", "रुचित": "रुच्",
    "सेव": "सेव्", "सेविष्य": "सेव्", "सेवितु": "सेव्", "सेवित": "सेव्",
    "लभ": "लभ्", "लप्स्य": "लभ्", "लब्धु": "लभ्", "लब्ध": "लभ्",
    "वर्त": "वृत्", "वर्तिष्य": "वृत्", "वर्तितु": "वृत्", "वृत्त": "वृत्",
    "भाष": "भाष्", "भाषिष्य": "भाष्", "भाषितु": "भाष्", "भाषित": "भाष्",
    "विद्य": "विद्", "वेत्ति": "विद्", "वेद": "विद्", "विदित": "विद्",
    "मन्य": "मन्", "मंस्य": "मन्", "मन्तु": "मन्", "मत": "मन्",
    "जाय": "जन्", "जनिष्य": "जन्", "जनितु": "जन्", "जात": "जन्",
    "शोभ": "शुभ्", "शोभिष्य": "शुभ्", "शोभितु": "शुभ्", "शोभित": "शुभ्",
    "यच्छ": "दा", "ददा": "दा", "दास्य": "दा", "दातु": "दा", "दत्त": "दा",
    "गृह्ण": "ग्रह्", "ग्रहीष्य": "ग्रह्", "ग्रहीतु": "ग्रह्", "गृहीत": "ग्रह्",
    "इच्छ": "इष्", "एषिष्य": "इष्", "एषितु": "इष्", "इष्ट": "इष्",
    "पृच्छ": "प्रछ्", "प्रक्ष्य": "प्रछ्", "प्रष्टु": "प्रछ्", "पृष्ट": "प्रछ्",
    "कथय": "कथ्", "कथिष्य": "कथ्", "कथितु": "कथ्", "कथित": "कथ्",
    "चिन्तय": "चिन्त्", "चिन्तिष्य": "चिन्त्", "चिन्तितु": "चिन्त्", "चिन्तित": "चिन्त्",
    "रक्ष": "रक्ष्", "रक्षिष्य": "रक्ष्", "रक्षितु": "रक्ष्", "रक्षित": "रक्ष्",
    "त्यज": "त्यज्", "त्यक्ष्य": "त्यज्", "त्यक्तु": "त्यज्", "त्यक्त": "त्यज्",
    "पत": "पत्", "पतिष्य": "पत्", "पतितु": "पत्", "पतित": "पत्",
    "वस": "वस्", "वत्स्य": "वस्", "वस्तु": "वस्", "उषित": "वस्",
    "मिल": "मिल्", "मिलिष्य": "मिल्", "मिलितु": "मिल्", "मिलित": "मिल्",
    "प्राप्नो": "आप्", "आप्नु": "आप्", "आप्स्य": "आप्", "आप्तु": "आप्", "आप्त": "आप्",
    "मोद": "मुद्", "मोदिष्य": "मुद्", "मोदितु": "मुद्", "मोदित": "मुद्",
}

# Suffix patterns for Kṛdanta (Participles) & Taddhita fallback
# (suffix, pratyaya_key, pos_label, trim_len)
KRDANTA_PATTERNS: List[Tuple[str, str, str, int]] = [
    # 1. Ktvā (क्त्वा)
    ("इत्वा", "ktvA", "Participle (कृदन्तपदम्)", 4),
    ("त्वा", "ktvA", "Participle (कृदन्तपदम्)", 3),
    # 2. Tumun (तुमुन्)
    ("ितुम्", "tumun", "Participle (कृदन्तपदम्)", 4),
    ("तुम्", "tumun", "Participle (कृदन्तपदम्)", 3),
    ("ष्टुम्", "tumun", "Participle (कृदन्तपदम्)", 4),
    # 3. Ktavatu (क्तवतु)
    ("ितवान्", "ktavatu", "Participle (कृदन्तपदम्)", 5),
    ("तवान्", "ktavatu", "Participle (कृदन्तपदम्)", 4),
    ("ितवती", "ktavatu", "Participle (कृदन्तपदम्)", 5),
    ("तवती", "ktavatu", "Participle (कृदन्तपदम्)", 4),
    ("ितवत्", "ktavatu", "Participle (कृदन्तपदम्)", 5),
    ("तवत्", "ktavatu", "Participle (कृदन्तपदम्)", 4),
    # 4. Tavyat (तव्यत्)
    ("ितव्यम्", "tavya", "Participle (कृदन्तपदम्)", 6),
    ("तव्यम्", "tavya", "Participle (कृदन्तपदम्)", 5),
    ("ितव्यः", "tavya", "Participle (कृदन्तपदम्)", 6),
    ("तव्यः", "tavya", "Participle (कृदन्तपदम्)", 5),
    ("ितव्या", "tavya", "Participle (कृदन्तपदम्)", 6),
    ("तव्या", "tavya", "Participle (कृदन्तपदम्)", 5),
    # 5. Anīyar (अनीयर)
    ("नीयम्", "anIya", "Participle (कृदन्तपदम्)", 4),
    ("नीयः", "anIya", "Participle (कृदन्तपदम्)", 4),
    ("नीया", "anIya", "Participle (कृदन्तपदम्)", 4),
    # 6. Kta (क्त)
    ("ितः", "kta", "Participle (कृदन्तपदम्)", 3),
    ("तः", "kta", "Participle (कृदन्तपदम्)", 2),
    ("िता", "kta", "Participle (कृदन्तपदम्)", 3),
    ("ता", "kta", "Participle (कृदन्तपदम्)", 2),
    ("ितम्", "kta", "Participle (कृदन्तपदम्)", 4),
    ("तम्", "kta", "Participle (कृदन्तपदम्)", 3),
    # 7. Śatṛ (शतृ - Present Participle Active)
    ("न्ती", "Satf", "Participle (कृदन्तपदम्)", 3),
    ("ती", "Satf", "Participle (कृदन्तपदम्)", 2),
    # 8. Śānac (शानच् - Present Participle Middle)
    ("मानः", "Sanac", "Participle (कृदन्तपदम्)", 4),
    ("माना", "Sanac", "Participle (कृदन्तपदम्)", 4),
    ("मानम्", "Sanac", "Participle (कृदन्तपदम्)", 5),
    ("आणः", "Sanac", "Participle (कृदन्तपदम्)", 4),
    ("आणा", "Sanac", "Participle (कृदन्तपदम्)", 4),
    ("आणम्", "Sanac", "Participle (कृदन्तपदम्)", 5),
    # 9. Taddhita: Matup / Vatup (मतुप् / वतुप्)
    ("वान्", "matup", "Adjective (तद्धितान्त-विशेषणम्)", 3),
    ("वती", "matup", "Adjective (तद्धितान्त-विशेषणम्)", 3),
    ("वत्", "matup", "Adjective (तद्धितान्त-विशेषणम्)", 2),
    ("मान्", "matup", "Adjective (तद्धितान्त-विशेषणम्)", 3),
    ("मती", "matup", "Adjective (तद्धितान्त-विशेषणम्)", 3),
    ("मत्", "matup", "Adjective (तद्धितान्त-विशेषणम्)", 2),
    # 10. Taddhita: Ṭhak (ठक् -> इक)
    ("िकः", "Wak", "Adjective (तद्धितान्त-विशेषणम्)", 3),
    ("िकी", "Wak", "Adjective (तद्धितान्त-विशेषणम्)", 3),
    ("िकम्", "Wak", "Adjective (तद्धितान्त-विशेषणम्)", 4),
    # 11. Taddhita: Tva (त्व) & Tal (तल्)
    ("त्वम्", "tva", "Noun / Substantive (भाववाचक-संज्ञा)", 4),
]

# Verb conjugation patterns covering all 5 CBSE/NCERT Lakāras:
# (suffix, lakara_key, purusha_key, vacana_key, trim_len)
TINANTA_PATTERNS: List[Tuple[str, str, str, str, int]] = [
    # 1. Simple Future (Lṛṭ - लृट्)
    ("िष्यति", "lfw", "praTamapuruzaH", "ekavacanam", 4),
    ("िष्यतः", "lfw", "praTamapuruzaH", "dvivacanam", 4),
    ("िष्यन्ति", "lfw", "praTamapuruzaH", "bahuvacanam", 5),
    ("िष्यसि", "lfw", "maDyamapuruzaH", "ekavacanam", 4),
    ("िष्यथः", "lfw", "maDyamapuruzaH", "dvivacanam", 4),
    ("िष्यथ", "lfw", "maDyamapuruzaH", "bahuvacanam", 4),
    ("िष्यामि", "lfw", "uttamapuruzaH", "ekavacanam", 4),
    ("िष्यावः", "lfw", "uttamapuruzaH", "dvivacanam", 4),
    ("िष्यामः", "lfw", "uttamapuruzaH", "bahuvacanam", 4),
    ("ष्यति", "lfw", "praTamapuruzaH", "ekavacanam", 3),
    ("ष्यतः", "lfw", "praTamapuruzaH", "dvivacanam", 3),
    ("ष्यन्ति", "lfw", "praTamapuruzaH", "bahuvacanam", 4),
    ("ष्यसि", "lfw", "maDyamapuruzaH", "ekavacanam", 3),
    ("ष्यथः", "lfw", "maDyamapuruzaH", "dvivacanam", 3),
    ("ष्यथ", "lfw", "maDyamapuruzaH", "bahuvacanam", 3),
    ("ष्यामि", "lfw", "uttamapuruzaH", "ekavacanam", 3),
    ("ष्यावः", "lfw", "uttamapuruzaH", "dvivacanam", 3),
    ("ष्यामः", "lfw", "uttamapuruzaH", "bahuvacanam", 3),
    ("स्यति", "lfw", "praTamapuruzaH", "ekavacanam", 3),
    ("स्यतः", "lfw", "praTamapuruzaH", "dvivacanam", 3),
    ("स्यन्ति", "lfw", "praTamapuruzaH", "bahuvacanam", 4),
    ("स्यसि", "lfw", "maDyamapuruzaH", "ekavacanam", 3),
    ("स्यामि", "lfw", "uttamapuruzaH", "ekavacanam", 3),
    ("स्यामः", "lfw", "uttamapuruzaH", "bahuvacanam", 3),

    # 2. Optative / Potential Mood (Vidhiliṅ - विधिलिङ्)
    ("ेताम्", "viDiliN", "praTamapuruzaH", "dvivacanam", 3),
    ("ेयुः", "viDiliN", "praTamapuruzaH", "bahuvacanam", 3),
    ("ेतम्", "viDiliN", "maDyamapuruzaH", "dvivacanam", 3),
    ("ेयम्", "viDiliN", "uttamapuruzaH", "ekavacanam", 3),
    ("ेत्", "viDiliN", "praTamapuruzaH", "ekavacanam", 2),
    ("ेः", "viDiliN", "maDyamapuruzaH", "ekavacanam", 2),
    ("ेत", "viDiliN", "maDyamapuruzaH", "bahuvacanam", 2),
    ("ेव", "viDiliN", "uttamapuruzaH", "dvivacanam", 2),
    ("ेम", "viDiliN", "uttamapuruzaH", "bahuvacanam", 2),

    # 3. Imperative Mood (Loṭ - लोट्)
    ("न्तु", "low", "praTamapuruzaH", "bahuvacanam", 3),
    ("ताम्", "low", "praTamapuruzaH", "dvivacanam", 3),
    ("तम्", "low", "maDyamapuruzaH", "dvivacanam", 3),
    ("आनि", "low", "uttamapuruzaH", "ekavacanam", 3),
    ("आव", "low", "uttamapuruzaH", "dvivacanam", 2),
    ("आम", "low", "uttamapuruzaH", "bahuvacanam", 2),
    ("तु", "low", "praTamapuruzaH", "ekavacanam", 2),

    # 4. Present Tense (Laṭ - लट् Parasmaipada)
    ("न्ति", "law", "praTamapuruzaH", "bahuvacanam", 3),
    ("थः", "law", "maDyamapuruzaH", "dvivacanam", 2),
    ("तः", "law", "praTamapuruzaH", "dvivacanam", 2),
    ("ति", "law", "praTamapuruzaH", "ekavacanam", 2),
    ("सि", "law", "maDyamapuruzaH", "ekavacanam", 2),
    ("थ", "law", "maDyamapuruzaH", "bahuvacanam", 1),
    ("मि", "law", "uttamapuruzaH", "ekavacanam", 2),
    ("वः", "law", "uttamapuruzaH", "dvivacanam", 2),
    ("मः", "law", "uttamapuruzaH", "bahuvacanam", 2),

    # 5. Passive Voice (कर्मणि प्रयोगः) & Present Ātmanepada (लट् आत्मनेपदम्)
    ("यन्ते", "law", "praTamapuruzaH", "bahuvacanam", 4),
    ("यते", "law", "praTamapuruzaH", "ekavacanam", 3),
    ("येते", "law", "praTamapuruzaH", "dvivacanam", 3),
    ("न्ते", "law", "praTamapuruzaH", "bahuvacanam", 3),
    ("एते", "law", "praTamapuruzaH", "dvivacanam", 3),
    ("ते", "law", "praTamapuruzaH", "ekavacanam", 2),
    ("से", "law", "maDyamapuruzaH", "ekavacanam", 2),
    ("ध्वे", "law", "maDyamapuruzaH", "bahuvacanam", 3),
    ("ामहे", "law", "uttamapuruzaH", "bahuvacanam", 4),
    ("ावहे", "law", "uttamapuruzaH", "dvivacanam", 4),
    ("महे", "law", "uttamapuruzaH", "bahuvacanam", 2),

    # 6. Ātmanepada Future (लृट्)
    ("िष्यन्ते", "lfw", "praTamapuruzaH", "bahuvacanam", 6),
    ("िष्यते", "lfw", "praTamapuruzaH", "ekavacanam", 5),
    ("स्यन्ते", "lfw", "praTamapuruzaH", "bahuvacanam", 5),
    ("स्यते", "lfw", "praTamapuruzaH", "ekavacanam", 4),

    # 7. Ātmanepada Imperative & Optative (लोट् एवं विधिलिङ्)
    ("न्ताम्", "low", "praTamapuruzaH", "bahuvacanam", 4),
    ("ताम्", "low", "praTamapuruzaH", "ekavacanam", 3),
    ("स्व", "low", "maDyamapuruzaH", "ekavacanam", 2),
    ("ेरन्", "viDiliN", "praTamapuruzaH", "bahuvacanam", 3),
]

# Suffix patterns for Subanta (Noun/Pronoun) fallback:
# (suffix, case_key, number_key, gender_key, trim_len)
SUBANTA_PATTERNS: List[Tuple[str, str, str, str, int]] = [
    # 6th plural -ānām / -āṇām
    ("ानाम्", "zazWIviBaktiH", "bahuvacanam", "puMlliNgam", 4),
    ("ाणाम्", "zazWIviBaktiH", "bahuvacanam", "puMlliNgam", 4),
    # Dual 3rd/4th/5th -ābhyām
    ("ाभ्याम्", "tftIyAviBaktiH", "dvivacanam", "puMlliNgam", 5),
    # Plural 4th/5th -ebhyaḥ
    ("ेभ्यः", "caturTIviBaktiH", "bahuvacanam", "puMlliNgam", 4),
    # Feminine ākārānta declensions
    ("ायाम्", "saptamIviBaktiH", "ekavacanam", "strIliNgam", 4),
    ("ायाः", "paYcamIviBaktiH", "ekavacanam", "strIliNgam", 4),
    ("ायै", "caturTIviBaktiH", "ekavacanam", "strIliNgam", 3),
    ("ासु", "saptamIviBaktiH", "bahuvacanam", "strIliNgam", 2),
    ("ाम्", "dvitIyAviBaktiH", "ekavacanam", "strIliNgam", 3),
    ("या", "tftIyAviBaktiH", "ekavacanam", "strIliNgam", 2),
    # Feminine īkārānta declensions (नदी, जननी)
    ("ीषु", "saptamIviBaktiH", "bahuvacanam", "strIliNgam", 2),
    ("ीभिः", "tftIyAviBaktiH", "bahuvacanam", "strIliNgam", 3),
    ("ीभ्यः", "caturTIviBaktiH", "bahuvacanam", "strIliNgam", 3),
    ("ीम्", "dvitIyAviBaktiH", "ekavacanam", "strIliNgam", 2),
    # Neuter plural 1st/2nd -āni / -āṇi
    ("ानि", "praTamAviBaktiH", "bahuvacanam", "napuMsakaliNgam", 3),
    ("ाणि", "praTamAviBaktiH", "bahuvacanam", "napuMsakaliNgam", 3),
    # 7th plural -eṣu
    ("ेषु", "saptamIviBaktiH", "bahuvacanam", "puMlliNgam", 2),
    # 6th singular -asya
    ("स्य", "zazWIviBaktiH", "ekavacanam", "puMlliNgam", 2),
    # 3rd singular -ena / -eṇa
    ("ेण", "tftIyAviBaktiH", "ekavacanam", "puMlliNgam", 2),
    ("ेन", "tftIyAviBaktiH", "ekavacanam", "puMlliNgam", 2),
    # 4th singular -āya
    ("ाय", "caturTIviBaktiH", "ekavacanam", "puMlliNgam", 2),
    # 5th singular -āt
    ("ात्", "paYcamIviBaktiH", "ekavacanam", "puMlliNgam", 3),
    # 3rd plural -aiḥ
    ("ैः", "tftIyAviBaktiH", "bahuvacanam", "puMlliNgam", 2),
    # 2nd plural -ān
    ("ान्", "dvitIyAviBaktiH", "bahuvacanam", "puMlliNgam", 2),
    # 1st plural -āḥ
    ("ाः", "praTamAviBaktiH", "bahuvacanam", "puMlliNgam", 2),
    # Ukārānta declensions (गुरु, साधु)
    ("वे", "caturTIviBaktiH", "ekavacanam", "puMlliNgam", 1),
    ("ोः", "zazWIviBaktiH", "ekavacanam", "puMlliNgam", 2),
    ("ून्", "dvitIyAviBaktiH", "bahuvacanam", "puMlliNgam", 2),
    ("ुषु", "saptamIviBaktiH", "bahuvacanam", "puMlliNgam", 2),
    # Dual 1st/2nd -au
    ("ौ", "praTamAviBaktiH", "dvivacanam", "puMlliNgam", 1),
    # 7th singular -e
    ("े", "saptamIviBaktiH", "ekavacanam", "napuMsakaliNgam", 1),
    # Consonantal declensions (मनस्, राजन्)
    ("मनसा", "tftIyAviBaktiH", "ekavacanam", "napuMsakaliNgam", 4),
    ("मनसि", "saptamIviBaktiH", "ekavacanam", "napuMsakaliNgam", 4),
    ("राज्ञा", "tftIyAviBaktiH", "ekavacanam", "puMlliNgam", 4),
    ("राज्ञे", "caturTIviBaktiH", "ekavacanam", "puMlliNgam", 4),
    ("विदुषा", "tftIyAviBaktiH", "ekavacanam", "puMlliNgam", 4),
    # 1st singular masculine -aḥ
    ("ः", "praTamAviBaktiH", "ekavacanam", "puMlliNgam", 1),
    # 2nd singular / Neuter nominative -am / -m
    ("म्", "dvitIyAviBaktiH", "ekavacanam", "napuMsakaliNgam", 2),
    ("ं", "dvitIyAviBaktiH", "ekavacanam", "napuMsakaliNgam", 1),
]

# ==============================================================================
# 4. CORE MORPHOLOGY ENGINE CLASS
# ==============================================================================

class MorphologyService:
    """
    Production Sanskrit Morphological Analysis Engine for NCERT Classes 6–10.
    Integrates the Sanskrit Heritage lexicon with automated Upasarga extraction,
    Kṛdanta participle mapping, deterministic Paninian rule fallbacks, and
    an in-memory token LRU cache for ultra-fast production performance.
    """

    _shared_analyzer: Optional[LexicalSandhiAnalyzer] = None
    _analyzer_lock: threading.Lock = threading.Lock()
    _shared_word_cache: OrderedDict[str, WordAnalysis] = OrderedDict()
    _shared_word_cache_lock: threading.Lock = threading.Lock()
    _default_max_token_cache: int = 8192
    _HASH_NUMBER_PATTERN = re.compile(r"#\d+")

    def __init__(self, max_token_cache: int = 8192):
        self._analyzer = self._get_analyzer()
        self._word_cache = self._shared_word_cache
        self._max_token_cache = max_token_cache
        self._word_cache_lock = self._shared_word_cache_lock

    @classmethod
    def _get_analyzer(cls) -> LexicalSandhiAnalyzer:
        """Thread-safe singleton getter to avoid duplicate loads of Heritage lexicon."""
        if cls._shared_analyzer is None:
            with cls._analyzer_lock:
                if cls._shared_analyzer is None:
                    cls._shared_analyzer = LexicalSandhiAnalyzer()
        return cls._shared_analyzer

    @staticmethod
    @lru_cache(maxsize=4096)
    def _devanagari_to_slp1(devanagari_text: str) -> str:
        """Converts Devanagari text to SLP1 encoding (LRU cached)."""
        return sanscript.transliterate(devanagari_text, sanscript.DEVANAGARI, sanscript.SLP1)

    @staticmethod
    @lru_cache(maxsize=4096)
    def _slp1_to_devanagari(slp1_text: Any) -> str:
        """Converts SLP1 transliterated root or token to Devanagari (LRU cached)."""
        clean_slp1 = MorphologyService._HASH_NUMBER_PATTERN.sub("", str(slp1_text)).strip()
        return sanscript.transliterate(clean_slp1, sanscript.SLP1, sanscript.DEVANAGARI)

    def _lookup_lexical_database(self, devanagari_token: str) -> List[Tuple[str, Set[str], Optional[str]]]:
        """
        Queries Sanskrit Heritage Lexicon using SLP1 phonetics with Paninian sandhi variants
        and automatic Upasarga (prefix) decomposition:
        1. Direct SLP1 form (e.g. pustakam, gacCati, gatvA).
        2. Padānta visarga to sakāra (e.g. rAmaH -> rAmas, bAlakaH -> bAlas, latAyAH -> latAyAs).
        3. Anusvāra to makāra (e.g. pustakaM -> pustakam).
        4. Upasarga prefix stripping with retroflex natva reversal (e.g. praRamati -> pra + namati).
        Returns list of (root_slp1, tag_set, detected_prefix_devanagari).
        """
        slp1_token = self._devanagari_to_slp1(devanagari_token)
        candidates_to_try: List[str] = [slp1_token]

        # Visarga sandhi variants
        if slp1_token.endswith("H"):
            candidates_to_try.append(slp1_token[:-1] + "s")
            candidates_to_try.append(slp1_token[:-1] + "r")
            if slp1_token.endswith("kaH"):
                candidates_to_try.append(slp1_token[:-3] + "s")
        if slp1_token.endswith("AH"):
            candidates_to_try.append(slp1_token[:-2] + "As")

        # Anusvara sandhi variant
        if slp1_token.endswith("M"):
            candidates_to_try.append(slp1_token[:-1] + "m")

        # 1. Try direct and phonetic sandhi lookups
        for cand in candidates_to_try:
            try:
                obj = SanskritNormalizedString(cand)
                results = self._analyzer.getMorphologicalTags(obj)
                if results:
                    return [(str(r), {str(t) for t in ts}, None) for r, ts in results]
            except Exception as e:
                logger.debug(f"Direct lexical lookup error on '{cand}': {e}")
                continue

        # 2. Try Upasarga (prefix) decomposition
        for upa_slp1, upa_dev in UPASARGAS_MAPPING:
            if slp1_token.startswith(upa_slp1) and len(slp1_token) > len(upa_slp1):
                remainder = slp1_token[len(upa_slp1):]
                rem_candidates = [remainder]

                # Retroflex reversal (e.g. pra + Ramati -> namati, pra + Ramya -> namya)
                if remainder.startswith("R"):
                    rem_candidates.append("n" + remainder[1:])
                # Consonant degemination (e.g. cC -> C)
                if remainder.startswith("cC"):
                    rem_candidates.append("C" + remainder[2:])
                # Visarga in remainder
                if remainder.endswith("H"):
                    rem_candidates.append(remainder[:-1] + "s")
                    rem_candidates.append(remainder[:-1] + "r")
                if remainder.endswith("AH"):
                    rem_candidates.append(remainder[:-2] + "As")
                # Anusvara in remainder
                if remainder.endswith("M"):
                    rem_candidates.append(remainder[:-1] + "m")

                for rc in rem_candidates:
                    try:
                        obj = SanskritNormalizedString(rc)
                        results = self._analyzer.getMorphologicalTags(obj)
                        if results:
                            return [(str(r), {str(t) for t in ts}, upa_dev) for r, ts in results]
                    except Exception as e:
                        logger.debug(f"Upasarga lookup error on remainder '{rc}': {e}")
                        continue

        return []

    def _convert_tags_to_gloss(
        self,
        root_slp1: Any,
        raw_tag_set: Set[Any],
        surface_word: str,
        prefix: Optional[str] = None
    ) -> Tuple[MorphologicalGloss, bool]:
        """
        Converts a raw Heritage tag set into student-friendly NCERT terminology,
        extracting prefixes, pratyayas (suffixes), grammatical voice, and lakāra.
        Returns (MorphologicalGloss, is_compound).
        """
        tag_set = {str(t) for t in raw_tag_set}
        raw_root_dev = self._slp1_to_devanagari(root_slp1)

        # Detect compound membership
        is_compound = "samAsapUrvapadanAmapadam" in tag_set or "samAsa" in tag_set

        # Canonicalize root if inflected participle stem was stored
        root_dev = DHATU_CANONICAL.get(raw_root_dev, raw_root_dev)

        # 1. Detect Part of Speech
        pos = "Noun / Substantive (नामपदम्)"
        is_verb = False
        is_participle = False
        is_avyaya = False

        krdanta_keys = {"ktvA", "lyap", "tumun", "Satf", "Sanac", "kta", "ktavatu", "tavya", "tavyat", "anIya", "anIyar", "kfdanta", "kfdantaH", "avyayaDAturUpa"}
        if "avyayam" in tag_set or "avyaya" in tag_set:
            if any(k in tag_set for k in ["ktvA", "lyap", "tumun"]):
                pos = "Participle (कृदन्तपदम्)"
                is_participle = True
            else:
                pos = "Indeclinable (अव्ययम्)"
                is_avyaya = True
        elif any(t in LAKARA_MAP for t in tag_set) or "tiNanta" in tag_set or ("prATamikaH" in tag_set and any(t in PURUSHA_MAP for t in tag_set)):
            pos = "Verb (क्रियापदम्)"
            is_verb = True
        elif any(k in tag_set for k in krdanta_keys):
            pos = "Participle (कृदन्तपदम्)"
            is_participle = True
        elif root_dev in ["तद्", "अस्मद्", "युष्मद्", "एतद्", "किम्", "इदम्", "सर्व", "भवत्"]:
            pos = "Pronoun (सर्वनाम)"

        # 2. Extract Pratyaya (Grammatical Suffix)
        pratyaya_val: Optional[str] = None
        for tag in tag_set:
            if tag in PRATYAYA_MAP:
                pratyaya_val = f"{PRATYAYA_MAP[tag][0]} / {PRATYAYA_MAP[tag][1]}"
                break

        # Paninian rule: समासेऽनञ्पूर्वे क्त्वो ल्यप् (७.१.३७)
        # Any prefixed verb form ending in -ya or -tya without case endings is an indeclinable gerund (Lyap)
        if prefix and surface_word.endswith(("य", "त्य")):
            pratyaya_val = f"{PRATYAYA_MAP['lyap'][0]} / {PRATYAYA_MAP['lyap'][1]}"
            pos = "Participle (कृदन्तपदम्)"
            is_participle = True
            is_avyaya = True
        elif is_participle and not pratyaya_val:
            if surface_word.endswith(("त्वा", "इत्वा")):
                pratyaya_val = "क्त्वा प्रत्ययः / Ktvā (having done / gerund)"
            elif surface_word.endswith(("य", "त्य")) and prefix:
                pratyaya_val = "ल्यप् प्रत्ययः / Lyap (having done with prefix / gerund)"
            elif surface_word.endswith(("तुम्", "ितुम्", "ष्टुम्")):
                pratyaya_val = "तुमुन् प्रत्ययः / Tumun (in order to / infinitive)"
            elif surface_word.endswith(("वान्", "वती", "वत्")):
                pratyaya_val = "क्तवतु प्रत्ययः / Ktavatu (past active participle)"
            elif surface_word.endswith(("तः", "ता", "तम्")):
                pratyaya_val = "क्त प्रत्ययः / Kta (past passive participle)"

        # 3. Extract Prayoga (Voice)
        voice_val: Optional[str] = None
        for tag in tag_set:
            if tag in PRAYOGA_MAP:
                voice_val = f"{PRAYOGA_MAP[tag][0]} / {PRAYOGA_MAP[tag][1]}"
                break
        if not voice_val:
            if is_verb or "ktavatu" in tag_set:
                voice_val = "कर्तरि प्रयोगः / Active Voice"
            elif "kta" in tag_set:
                voice_val = "कर्मणि प्रयोगः / Passive Voice"

        # 4. Extract Vibhakti (Case) - indeclinables do not decline
        case_val = None
        if not is_avyaya and not (is_participle and pratyaya_val and ("Ktvā" in pratyaya_val or "Lyap" in pratyaya_val or "Tumun" in pratyaya_val)):
            for tag in tag_set:
                if tag in VIBHAKTI_MAP:
                    case_val = f"{VIBHAKTI_MAP[tag][1]} / {VIBHAKTI_MAP[tag][0]}"
                    break

        # 5. Extract Linga (Gender)
        gender_val = None
        if not is_avyaya and not (is_participle and pratyaya_val and ("Ktvā" in pratyaya_val or "Lyap" in pratyaya_val or "Tumun" in pratyaya_val)):
            for tag in tag_set:
                if tag in LINGA_MAP:
                    gender_val = f"{LINGA_MAP[tag][1]} / {LINGA_MAP[tag][0]}"
                    break

        # 6. Extract Vacana (Number)
        vacana_val = None
        for tag in tag_set:
            if tag in VACANA_MAP:
                vacana_val = f"{VACANA_MAP[tag][1]} / {VACANA_MAP[tag][0]}"
                break

        # 7. Extract Lakāra (Tense / Mood)
        tense_val = None
        for tag in tag_set:
            if tag in LAKARA_MAP:
                tense_val = f"{LAKARA_MAP[tag][1]} / {LAKARA_MAP[tag][0]}"
                break

        # 8. Extract Puruṣa (Person)
        person_val = None
        for tag in tag_set:
            if tag in PURUSHA_MAP:
                person_val = f"{PURUSHA_MAP[tag][1]} / {PURUSHA_MAP[tag][0]}"
                break

        # 9. Format Upasarga prefix string
        prefix_val: Optional[str] = None
        if prefix:
            prefix_val = f"{prefix}"

        # 10. Build Student-Friendly Pedagogical Explanations
        if is_verb and tense_val and person_val and vacana_val:
            prefix_skt = f"उपसर्गः: {prefix_val} + " if prefix_val else ""
            prefix_eng = f"Prefix: '{prefix_val}', " if prefix_val else ""
            sanskrit_exp = f"{prefix_skt}मूलधातुः: {root_dev} | {tense_val.split(' / ')[1]} | {person_val.split(' / ')[1]} | {vacana_val.split(' / ')[1]}"
            if voice_val:
                sanskrit_exp += f" | {voice_val.split(' / ')[0]}"
            english_exp = f"{prefix_eng}Root: '{root_dev}', Verb conjugated in {tense_val.split(' / ')[0]}, {person_val.split(' / ')[0]}, {vacana_val.split(' / ')[0]}"
            if voice_val:
                english_exp += f" ({voice_val.split(' / ')[1]})"

        elif is_participle:
            prat_skt = pratyaya_val.split(' / ')[0] if pratyaya_val else "कृदन्त प्रत्ययः"
            prat_eng = pratyaya_val.split(' / ')[1] if pratyaya_val else "participle suffix"
            prefix_skt = f"उपसर्गः: {prefix_val} + " if prefix_val else ""
            prefix_eng = f"Prefix: '{prefix_val}', " if prefix_val else ""

            if case_val and vacana_val:
                gen_skt = gender_val.split(' / ')[1] if gender_val else 'पुंल्लिङ्गम्'
                gen_eng = gender_val.split(' / ')[0] if gender_val else 'Masculine'
                sanskrit_exp = f"{prefix_skt}मूलधातुः: {root_dev} | {prat_skt} | {gen_skt} | {case_val.split(' / ')[1]} | {vacana_val.split(' / ')[1]}"
                english_exp = f"{prefix_eng}Root: '{root_dev}', Participle formed with {prat_eng} in {gen_eng}, {case_val.split(' / ')[0]}, {vacana_val.split(' / ')[0]}"
            else:
                sanskrit_exp = f"{prefix_skt}मूलधातुः: {root_dev} | {prat_skt} (कृदन्त अव्ययपदम्)"
                english_exp = f"{prefix_eng}Root: '{root_dev}', Indeclinable participle formed with {prat_eng}"

        elif is_avyaya:
            meaning = NCERT_AVYAYAS.get(surface_word, (surface_word, "indeclinable particle"))[1]
            sanskrit_exp = f"अव्ययपदम् | मूलम्: {root_dev} | अर्थः: {meaning}"
            english_exp = f"Indeclinable particle ('{meaning}') — never changes across gender, case, or number."

        elif case_val and vacana_val:
            gen_skt = gender_val.split(' / ')[1] if gender_val else 'पदम्'
            gen_eng = gender_val.split(' / ')[0] if gender_val else 'Noun'
            sanskrit_exp = f"मूलप्रातिपदिकम्: {root_dev} | {gen_skt} | {case_val.split(' / ')[1]} | {vacana_val.split(' / ')[1]}"
            english_exp = f"Stem: '{root_dev}', {gen_eng}, {case_val.split(' / ')[0]}, {vacana_val.split(' / ')[0]}"
        else:
            sanskrit_exp = f"पदम्: {surface_word} | मूलम्: {root_dev} ({pos})"
            english_exp = f"Word: '{surface_word}', Root/Stem: '{root_dev}' ({pos})"

        gloss = MorphologicalGloss(
            root=root_dev,
            pos=pos,
            gender=gender_val,
            case=case_val,
            number=vacana_val,
            tense=tense_val,
            person=person_val,
            prefix=prefix_val,
            pratyaya=pratyaya_val,
            voice=voice_val,
            sanskrit_explanation=sanskrit_exp,
            english_explanation=english_exp,
        )
        return gloss, is_compound

    def _fallback_analysis(self, token: str) -> WordAnalysis:
        """
        Deterministic rule-based fallback engine for CBSE/NCERT Sanskrit.
        Ensures 100% resolution for all 5 Lakāras, textbook participles (Kṛdanta),
        subanta nominal cases, and textbook avyayas.
        """
        clean = token.strip("।,॥.?!")

        # 1. Check NCERT Avyaya dictionary
        if clean in NCERT_AVYAYAS:
            root_word, meaning = NCERT_AVYAYAS[clean]
            gloss = MorphologicalGloss(
                root=root_word,
                pos="Indeclinable (अव्ययम्)",
                gender=None,
                case=None,
                number=None,
                tense=None,
                person=None,
                prefix=None,
                pratyaya=None,
                voice=None,
                sanskrit_explanation=f"अव्ययपदम् | अर्थः: {meaning}",
                english_explanation=f"Indeclinable particle ('{meaning}') — never changes across gender, case, or number.",
            )
            return WordAnalysis(word=token, primary_gloss=gloss, confidence=0.98)

        # 1.1 Check Enclitic & Irregular Pronouns (मे, ते, नौ, वाम्, नः, वः)
        ENCLITIC_PRONOUNS: Dict[str, Dict[str, str]] = {
            "मे": {
                "root": "अस्मद्",
                "pos": "Pronoun (सर्वनाम)",
                "gender": "त्रिषु लिङ्गेषु समानम् / All Genders",
                "case": "Dative / Genitive (चतुर्थी / षष्ठी विभक्तिः)",
                "number": "Singular / एकवचनम्",
                "sanskrit": "अस्मद्-सर्वनाम | चतुर्थी/षष्ठी विभक्तिः (मह्यम् / मम इत्यर्थे)",
                "english": "1st-person enclitic pronoun 'अस्मद्' in Dative or Genitive ('to me' / 'my').",
            },
            "ते": {
                "root": "युष्मद्",
                "pos": "Pronoun (सर्वनाम)",
                "gender": "त्रिषु लिङ्गेषु समानम् / All Genders",
                "case": "Dative / Genitive (चतुर्थी / षष्ठी विभक्तिः)",
                "number": "Singular / एकवचनम्",
                "sanskrit": "युष्मद्-सर्वनाम | चतुर्थी/षष्ठी विभक्तिः (तुभ्यम् / तव इत्यर्थे)",
                "english": "2nd-person enclitic pronoun 'युष्मद्' in Dative or Genitive ('to you' / 'your').",
            },
            "नः": {
                "root": "अस्मद्",
                "pos": "Pronoun (सर्वनाम)",
                "gender": "त्रिषु लिङ्गेषु समानम् / All Genders",
                "case": "Accusative / Dative / Genitive (द्वितीया / चतुर्थी / षष्ठी)",
                "number": "Plural / बहुवचनम्",
                "sanskrit": "अस्मद्-सर्वनाम | द्वितीया/चतुर्थी/षष्ठी (अस्मान् / अस्मभ्यम् / अस्माकम् इत्यर्थे)",
                "english": "1st-person enclitic pronoun 'अस्मद्' in Accusative, Dative, or Genitive Plural ('us' / 'to us' / 'our').",
            },
            "वः": {
                "root": "युष्मद्",
                "pos": "Pronoun (सर्वनाम)",
                "gender": "त्रिषु लिङ्गेषु समानम् / All Genders",
                "case": "Accusative / Dative / Genitive (द्वितीया / चतुर्थी / षष्ठी)",
                "number": "Plural / बहुवचनम्",
                "sanskrit": "युष्मद्-सर्वनाम | द्वितीया/चतुर्थी/षष्ठी (युष्मान् / युष्मभ्यम् / युष्माकम् इत्यर्थे)",
                "english": "2nd-person enclitic pronoun 'युष्मद्' in Accusative, Dative, or Genitive Plural ('you' / 'to you' / 'your').",
            },
        }
        if clean in ENCLITIC_PRONOUNS:
            enc = ENCLITIC_PRONOUNS[clean]
            gloss = MorphologicalGloss(
                root=enc["root"],
                pos=enc["pos"],
                gender=enc["gender"],
                case=enc["case"],
                number=enc["number"],
                tense=None,
                person=None,
                prefix=None,
                pratyaya=None,
                voice=None,
                sanskrit_explanation=enc["sanskrit"],
                english_explanation=enc["english"],
            )
            return WordAnalysis(word=token, primary_gloss=gloss, confidence=0.96)

        # 2. Check Lyap Participles with Upasargas (e.g. प्रणम्य, आगत्य, विज्ञाय, उपगम्य)
        if clean.endswith(("य", "त्य")):
            for upa_slp1, upa_dev in UPASARGAS_MAPPING:
                if clean.startswith(upa_dev) and len(clean) > len(upa_dev):
                    stem = clean[len(upa_dev):]
                    stem = stem[:-2] if stem.endswith("त्य") else stem[:-1]
                    root_raw = DHATU_CANONICAL.get(stem, stem + "्" if stem else clean)
                    prat_label = "ल्यप् प्रत्ययः / Lyap (having done with prefix / gerund)"
                    gloss = MorphologicalGloss(
                        root=root_raw,
                        pos="Participle (कृदन्तपदम्)",
                        gender=None,
                        case=None,
                        number=None,
                        tense=None,
                        person=None,
                        prefix=upa_dev,
                        pratyaya=prat_label,
                        voice="कर्तरि प्रयोगः / Active Voice",
                        sanskrit_explanation=f"उपसर्गः: {upa_dev} + मूलधातुः: {root_raw} | ल्यप् प्रत्ययः (पूर्वकालिक कृदन्त अव्ययपदम्)",
                        english_explanation=f"Prefix: '{upa_dev}', Root: '{root_raw}', Indeclinable past participle formed with 'ल्यप्' (lyap) suffix (having done action).",
                    )
                    return WordAnalysis(word=token, primary_gloss=gloss, confidence=0.94)

        # 3. Check General Kṛdanta & Taddhita Participle Patterns
        for suffix, pratyaya_key, pos_label, trim_len in KRDANTA_PATTERNS:
            if clean.endswith(suffix):
                stem = clean[:-trim_len]
                root_raw = DHATU_CANONICAL.get(stem, stem + "्" if stem else clean)
                prat_val = f"{PRATYAYA_MAP.get(pratyaya_key, (pratyaya_key, pratyaya_key))[0]} / {PRATYAYA_MAP.get(pratyaya_key, (pratyaya_key, pratyaya_key))[1]}"

                # Gender/case details for declined participles & taddhitas
                gen_val = None
                case_val = None
                num_val = None
                voice_val = "कर्तरि प्रयोगः / Active Voice"

                if pratyaya_key == "ktavatu":
                    gen_val = "Masculine / पुंल्लिङ्गम्" if suffix.endswith("वान्") else ("Feminine / स्त्रीलिङ्गम्" if suffix.endswith("वती") else "Neuter / नपुंसकलिङ्गम्")
                    case_val = "Nominative (1st Case) / प्रथमा विभक्तिः (कर्ता)"
                    num_val = "Singular / एकवचनम्"
                    skt_exp = f"मूलधातुः: {root_raw} | {PRATYAYA_MAP[pratyaya_key][0]} | {gen_val.split(' / ')[1]} | {case_val.split(' / ')[1]} | {num_val.split(' / ')[1]}"
                    eng_exp = f"Root: '{root_raw}', Past active participle formed with {PRATYAYA_MAP[pratyaya_key][1]} in {gen_val.split(' / ')[0]}, {case_val.split(' / ')[0]}, {num_val.split(' / ')[0]}."
                elif pratyaya_key == "kta":
                    voice_val = "कर्मणि प्रयोगः / Passive Voice"
                    gen_val = "Masculine / पुंल्लिङ्गम्" if suffix.endswith("तः") else ("Feminine / स्त्रीलिङ्गम्" if suffix.endswith("ता") else "Neuter / नपुंसकलिङ्गम्")
                    case_val = "Nominative (1st Case) / प्रथमा विभक्तिः (कर्ता)"
                    num_val = "Singular / एकवचनम्"
                    skt_exp = f"मूलधातुः: {root_raw} | {PRATYAYA_MAP[pratyaya_key][0]} | {gen_val.split(' / ')[1]} | {case_val.split(' / ')[1]} | {num_val.split(' / ')[1]}"
                    eng_exp = f"Root: '{root_raw}', Past passive participle formed with {PRATYAYA_MAP[pratyaya_key][1]} in {gen_val.split(' / ')[0]}, {case_val.split(' / ')[0]}, {num_val.split(' / ')[0]}."
                elif pratyaya_key == "Satf":
                    gen_val = "Feminine / स्त्रीलिङ्गम्"
                    case_val = "Nominative (1st Case) / प्रथमा विभक्तिः (कर्ता)"
                    num_val = "Singular / एकवचनम्"
                    skt_exp = f"मूलधातुः: {root_raw} | {PRATYAYA_MAP[pratyaya_key][0]} | स्त्रीलिङ्गम् | प्रथमा विभक्तिः | एकवचनम्"
                    eng_exp = f"Root: '{root_raw}', Present active participle (while doing action) in Feminine Singular."
                elif pratyaya_key == "Sanac":
                    gen_val = "Masculine / पुंल्लिङ्गम्" if suffix.endswith("ः") else ("Feminine / स्त्रीलिङ्गम्" if suffix.endswith("ा") else "Neuter / नपुंसकलिङ्गम्")
                    case_val = "Nominative (1st Case) / प्रथमा विभक्तिः (कर्ता)"
                    num_val = "Singular / एकवचनम्"
                    skt_exp = f"मूलधातुः: {root_raw} | {PRATYAYA_MAP[pratyaya_key][0]} | {gen_val.split(' / ')[1]} | प्रथमा विभक्तिः | एकवचनम्"
                    eng_exp = f"Root: '{root_raw}', Present middle participle (while doing action) in {gen_val.split(' / ')[0]} Singular."
                elif pratyaya_key == "matup":
                    voice_val = None
                    gen_val = "Masculine / पुंल्लिङ्गम्" if suffix.endswith("न्") else ("Feminine / स्त्रीलिङ्गम्" if suffix.endswith("ी") else "Neuter / नपुंसकलिङ्गम्")
                    case_val = "Nominative (1st Case) / प्रथमा विभक्तिः (कर्ता)"
                    num_val = "Singular / एकवचनम्"
                    skt_exp = f"मूलप्रातिपदिकम्: {stem} | {PRATYAYA_MAP[pratyaya_key][0]} | {gen_val.split(' / ')[1]} | प्रथमा विभक्तिः"
                    eng_exp = f"Stem: '{stem}', Possessive adjective formed with Matup ('possessing {stem}') in {gen_val.split(' / ')[0]} Singular."
                elif pratyaya_key == "Wak":
                    THAK_VRIDDHI_STEMS: Dict[str, str] = {
                        "धार्म": "धर्म", "सामाज": "समाज", "दैन": "दिन",
                        "ऐतिहास": "इतिहास", "भौगोल": "भूगोल", "शारीर": "शरीर",
                        "आर्थ": "अर्थ", "सप्ताह": "सप्ताह", "मास": "मास",
                        "वर्ष": "वर्ष", "व्यावहार": "व्यवहार", "नैन": "नीति",
                        "वैद": "वेद",
                    }
                    stem = THAK_VRIDDHI_STEMS.get(stem, stem)
                    voice_val = None
                    gen_val = "Masculine / पुंल्लिङ्गम्" if suffix.endswith("ः") else ("Feminine / स्त्रीलिङ्गम्" if suffix.endswith("ी") else "Neuter / नपुंसकलिङ्गम्")
                    case_val = "Nominative (1st Case) / प्रथमा विभक्तिः (कर्ता)"
                    num_val = "Singular / एकवचनम्"
                    skt_exp = f"मूलप्रातिपदिकम्: {stem} | {PRATYAYA_MAP[pratyaya_key][0]} | {gen_val.split(' / ')[1]} | प्रथमा विभक्तिः"
                    eng_exp = f"Stem: '{stem}', Derivational adjective formed with Ṭhak ('pertaining to {stem}') in {gen_val.split(' / ')[0]}."
                elif pratyaya_key in ["tva", "tal"]:
                    voice_val = None
                    gen_val = "Neuter / नपुंसकलिङ्गम्" if pratyaya_key == "tva" else "Feminine / स्त्रीलिङ्गम्"
                    case_val = "Nominative (1st Case) / प्रथमा विभक्तिः (कर्ता)"
                    num_val = "Singular / एकवचनम्"
                    skt_exp = f"मूलप्रातिपदिकम्: {stem} | {PRATYAYA_MAP[pratyaya_key][0]} | भाववाचक-संज्ञा"
                    eng_exp = f"Stem: '{stem}', Abstract noun formed with {PRATYAYA_MAP[pratyaya_key][1]} ('state of {stem}')."
                else:
                    skt_exp = f"मूलधातुः: {root_raw} | {PRATYAYA_MAP[pratyaya_key][0]} (कृदन्त अव्ययपदम्)"
                    eng_exp = f"Root: '{root_raw}', Indeclinable participle formed with {PRATYAYA_MAP[pratyaya_key][1]}."

                gloss = MorphologicalGloss(
                    root=root_raw if pratyaya_key not in ["matup", "Wak", "tva", "tal"] else stem,
                    pos=pos_label,
                    gender=gen_val,
                    case=case_val,
                    number=num_val,
                    tense=None,
                    person=None,
                    prefix=None,
                    pratyaya=prat_val,
                    voice=voice_val,
                    sanskrit_explanation=skt_exp,
                    english_explanation=eng_exp,
                )
                return WordAnalysis(word=token, primary_gloss=gloss, confidence=0.93)

        # 4. Check Śatṛ masculine active participles (e.g. पठन्, गच्छन्, कुर्वन्, पश्यन्, हसन्, वदन्)
        if clean.endswith("न्") and len(clean) >= 3 and not clean.endswith(("वान्", "मान्", "ान्", "ीन्", "ून्")):
            base_cand = clean[:-1]
            if base_cand in DHATU_CANONICAL or (base_cand + "ति") in DHATU_CANONICAL or base_cand in ["पठ", "गच्छ", "कुर्व", "पश्य", "हस", "वद", "धाव", "पिब", "तिष्ठ"]:
                root_raw = DHATU_CANONICAL.get(base_cand, base_cand + "्")
                prat_val = f"{PRATYAYA_MAP['Satf'][0]} / {PRATYAYA_MAP['Satf'][1]}"
                gloss = MorphologicalGloss(
                    root=root_raw,
                    pos="Participle (कृदन्तपदम्)",
                    gender="Masculine / पुंल्लिङ्गम्",
                    case="Nominative (1st Case) / प्रथमा विभक्तिः (कर्ता)",
                    number="Singular / एकवचनम्",
                    tense=None,
                    person=None,
                    prefix=None,
                    pratyaya=prat_val,
                    voice="कर्तरि प्रयोगः / Active Voice",
                    sanskrit_explanation=f"मूलधातुः: {root_raw} | शतृ प्रत्ययः | पुंल्लिङ्गम् | प्रथमा विभक्तिः | एकवचनम्",
                    english_explanation=f"Root: '{root_raw}', Present active participle (while doing action) in Masculine Nominative Singular.",
                )
                return WordAnalysis(word=token, primary_gloss=gloss, confidence=0.93)

        # 5. Check Past Imperfect Tense (Laṅ - लङ्) with initial 'a-' augment
        # e.g. अपठत्, अगच्छत्, अवदत्, अपठताम्, अपठन्
        if clean.startswith("अ") and len(clean) >= 4:
            lan_stem = clean[1:]  # strip augment 'a'
            lan_suffixes = [
                ("ताम्", "praTamapuruzaH", "dvivacanam", 3),
                ("तम्", "maDyamapuruzaH", "dvivacanam", 3),
                ("त्", "praTamapuruzaH", "ekavacanam", 2),
                ("न्", "praTamapuruzaH", "bahuvacanam", 2),
                ("ः", "maDyamapuruzaH", "ekavacanam", 1),
                ("त", "maDyamapuruzaH", "bahuvacanam", 1),
                ("म्", "uttamapuruzaH", "ekavacanam", 2),
                ("व", "uttamapuruzaH", "dvivacanam", 1),
                ("म", "uttamapuruzaH", "bahuvacanam", 1),
            ]
            for sfx, p_key, v_key, t_len in lan_suffixes:
                if lan_stem.endswith(sfx):
                    base_verb = lan_stem[:-t_len]

                    # Validate that base_verb is a genuine classical verb root for ambiguous visarga/anusvara endings
                    # to prevent common nouns starting with 'a-' (e.g. अर्थः, अश्वः, अनलः, अमृतम्, असुरः) from being misclassified as verbs
                    if sfx in ["ः", "म्"]:
                        is_valid_lan_root = (
                            base_verb in DHATU_CANONICAL
                            or (base_verb + "ति") in DHATU_CANONICAL
                            or (base_verb + "ते") in DHATU_CANONICAL
                            or base_verb in ["पठ", "गच्छ", "वद", "लिख", "हस", "धाव", "पिब", "तिष्ठ", "भव", "कुरु", "नय", "हर", "स्मर", "खाद", "नम", "जीव", "शृणु", "कथय", "चिन्तय", "रक्ष", "त्यज", "पत", "वस", "मिल", "शोभ", "रोच", "सेव", "लभ", "पश्य"]
                        )
                        if not is_valid_lan_root:
                            continue

                    root_raw = DHATU_CANONICAL.get(base_verb, base_verb + "्" if base_verb else clean)
                    tense_val = f"{LAKARA_MAP['laN'][1]} / {LAKARA_MAP['laN'][0]}"
                    person_val = f"{PURUSHA_MAP[p_key][1]} / {PURUSHA_MAP[p_key][0]}"
                    vacana_val = f"{VACANA_MAP[v_key][1]} / {VACANA_MAP[v_key][0]}"
                    gloss = MorphologicalGloss(
                        root=root_raw,
                        pos="Verb (क्रियापदम्)",
                        gender=None,
                        case=None,
                        number=vacana_val,
                        tense=tense_val,
                        person=person_val,
                        prefix=None,
                        pratyaya=None,
                        voice="कर्तरि प्रयोगः / Active Voice",
                        sanskrit_explanation=f"धातुः: {root_raw} | {LAKARA_MAP['laN'][0]} | {PURUSHA_MAP[p_key][0]} | {VACANA_MAP[v_key][0]} | कर्तरि प्रयोगः",
                        english_explanation=f"Root: '{root_raw}', Verb conjugated in {LAKARA_MAP['laN'][1]}, {PURUSHA_MAP[p_key][1]}, {VACANA_MAP[v_key][1]} (Active Voice).",
                    )
                    return WordAnalysis(word=token, primary_gloss=gloss, confidence=0.92)

        # 6. Check Tiṅanta (Verb) Suffix Patterns for other Lakāras (Lṛṭ, Loṭ, Vidhiliṅ, Laṭ)
        for suffix, lakara_key, purusha_key, vacana_key, trim_len in TINANTA_PATTERNS:
            if clean.endswith(suffix):
                stem = clean[:-trim_len]

                # Suffixes with visarga like "थः", "तः", "वः", "मः", "थ" easily collide with common masculine
                # nouns ending in -aḥ (e.g. अर्थः, ग्रन्थः, रथः, दूतः, पर्वतः, हस्तः, देवः, ग्रामः).
                # Require stem to be a known verbal base unless suffix is a distinct multi-syllable verb ending
                if suffix in ["थः", "तः", "वः", "मः", "थ"]:
                    is_known_dhatu = (
                        stem in DHATU_CANONICAL
                        or (stem + "ति") in DHATU_CANONICAL
                        or stem in ["पठ", "गच्छ", "वद", "लिख", "हस", "धाव", "पिब", "तिष्ठ", "भव", "कुरु", "नय", "हर", "स्मर", "खाद", "नम", "जीव", "शृणु", "कथ", "कथय", "चिन्त", "चिन्तय", "रक्ष", "जाना", "पश्य"]
                    )
                    if not is_known_dhatu:
                        continue

                root_raw = DHATU_CANONICAL.get(stem, stem + "्" if stem else clean)
                tense_val = f"{LAKARA_MAP[lakara_key][1]} / {LAKARA_MAP[lakara_key][0]}"
                person_val = f"{PURUSHA_MAP[purusha_key][1]} / {PURUSHA_MAP[purusha_key][0]}"
                vacana_val = f"{VACANA_MAP[vacana_key][1]} / {VACANA_MAP[vacana_key][0]}"

                if suffix in ["यते", "यन्ते", "येते"]:
                    voice_val = "कर्मणि प्रयोगः / Passive Voice"
                elif suffix in ["न्ते", "एते", "ते", "से", "ध्वे", "ामहे", "ावहे", "महे", "िष्यन्ते", "िष्यते", "स्यन्ते", "स्यते", "न्ताम्", "ताम्", "स्व", "ेरन्", "ेत"]:
                    voice_val = "आत्मनेपदम् (कर्तरि प्रयोगः) / Atmanepada (Active Voice)"
                else:
                    voice_val = "परस्मैपदम् (कर्तरि प्रयोगः) / Parasmaipada (Active Voice)"

                gloss = MorphologicalGloss(
                    root=root_raw,
                    pos="Verb (क्रियापदम्)",
                    gender=None,
                    case=None,
                    number=vacana_val,
                    tense=tense_val,
                    person=person_val,
                    prefix=None,
                    pratyaya=None,
                    voice=voice_val,
                    sanskrit_explanation=f"धातुः: {root_raw} | {LAKARA_MAP[lakara_key][0]} | {PURUSHA_MAP[purusha_key][0]} | {VACANA_MAP[vacana_key][0]} | {voice_val.split(' / ')[0]}",
                    english_explanation=f"Root: '{root_raw}', Verb conjugated in {LAKARA_MAP[lakara_key][1]}, {PURUSHA_MAP[purusha_key][1]}, {VACANA_MAP[vacana_key][1]} ({voice_val.split(' / ')[1]}).",
                )
                return WordAnalysis(word=token, primary_gloss=gloss, confidence=0.92)

        # 6. Check Subanta (Noun) Suffix Patterns across all 7 cases
        for suffix, case_key, vacana_key, linga_key, trim_len in SUBANTA_PATTERNS:
            if clean.endswith(suffix):
                stem = clean[:-trim_len]
                root_raw = stem if stem.endswith(("ा", "ी", "ू")) else (stem if stem else clean)
                case_val = f"{VIBHAKTI_MAP[case_key][1]} / {VIBHAKTI_MAP[case_key][0]}"
                vacana_val = f"{VACANA_MAP[vacana_key][1]} / {VACANA_MAP[vacana_key][0]}"
                linga_val = f"{LINGA_MAP[linga_key][1]} / {LINGA_MAP[linga_key][0]}"
                gloss = MorphologicalGloss(
                    root=root_raw if root_raw else clean,
                    pos="Noun / Substantive (नामपदम् / संज्ञा)",
                    gender=linga_val,
                    case=case_val,
                    number=vacana_val,
                    tense=None,
                    person=None,
                    prefix=None,
                    pratyaya=None,
                    voice=None,
                    sanskrit_explanation=f"प्रातिपदिकम्: {root_raw} | {LINGA_MAP[linga_key][0]} | {VIBHAKTI_MAP[case_key][0]} | {VACANA_MAP[vacana_key][0]}",
                    english_explanation=f"Stem: '{root_raw}', {LINGA_MAP[linga_key][1]} noun declined in {VIBHAKTI_MAP[case_key][1]}, {VACANA_MAP[vacana_key][1]}.",
                )
                return WordAnalysis(word=token, primary_gloss=gloss, confidence=0.90)

        # 7. Universal Default Fallback
        default_gloss = MorphologicalGloss(
            root=clean,
            pos="Noun / Proper Noun (संज्ञापदम्)",
            gender="Masculine / पुंल्लिङ्गम्",
            case="Nominative (1st Case) / प्रथमा विभक्तिः (कर्ता)",
            number="Singular / एकवचनम्",
            tense=None,
            person=None,
            prefix=None,
            pratyaya=None,
            voice=None,
            sanskrit_explanation=f"प्रातिपदिकम्: {clean} | नामपदम्",
            english_explanation=f"Base word: '{clean}' (Sanskrit textbook noun/name).",
        )
        return WordAnalysis(word=token, primary_gloss=default_gloss, confidence=0.80)

    def _lookup_modern_lexicon(self, clean_word: str) -> Optional[WordAnalysis]:
        """
        Resolves modern Sanskrit neologisms and borrowed technology/transportation terms
        defined by the Central Sanskrit University, including inflected forms.
        """
        # 1. Exact uninflected / canonical match
        if clean_word in MODERN_SANSKRIT_TERMS:
            lemma, meaning, category, gender = MODERN_SANSKRIT_TERMS[clean_word]
            gloss = MorphologicalGloss(
                root=lemma,
                pos="Modern Noun (आधुनिक-संज्ञापदम्)",
                gender=gender,
                case="Nominative (1st Case) / प्रथमा विभक्तिः (कर्ता)",
                number="Singular / एकवचनम्",
                tense=None,
                person=None,
                prefix=None,
                pratyaya=None,
                voice=None,
                sanskrit_explanation=f"आधुनिक-संस्कृत-पदम् | वर्गः: {category} | अर्थः: {meaning} | {gender}",
                english_explanation=f"Modern Sanskrit term: '{lemma}' ({meaning}), {category}.",
            )
            return WordAnalysis(word=clean_word, primary_gloss=gloss, confidence=0.98)

        # 2. Inflection peeling on a-stem and standard nominal declensions
        MODERN_DECLENSIONS = [
            ("ेण", "तृतीया विभक्तिः (करण)", "Instrumental (3rd Case)", "Singular / एकवचनम्", 2),
            ("ेन", "तृतीया विभक्तिः (करण)", "Instrumental (3rd Case)", "Singular / एकवचनम्", 2),
            ("ाय", "चतुर्थी विभक्तिः (सम्प्रदान)", "Dative (4th Case)", "Singular / एकवचनम्", 2),
            ("ात्", "पञ्चमी विभक्तिः (अपादान)", "Ablative (5th Case)", "Singular / एकवचनम्", 3),
            ("ात", "पञ्चमी विभक्तिः (अपादान)", "Ablative (5th Case)", "Singular / एकवचनम्", 2),
            ("स्य", "षष्ठी विभक्तिः (सम्बन्ध)", "Genitive (6th Case)", "Singular / एकवचनम्", 3),
            ("े", "सप्तमी विभक्तिः (अधिकरण)", "Locative (7th Case)", "Singular / एकवचनम्", 1),
            ("ाणि", "प्रथमा/द्वितीया विभक्तिः", "Nominative / Accusative", "Plural / बहुवचनम्", 3),
            ("ैः", "तृतीया विभक्तिः (करण)", "Instrumental (3rd Case)", "Plural / बहुवचनम्", 2),
            ("ेषु", "सप्तमी विभक्तिः (अधिकरण)", "Locative (7th Case)", "Plural / बहुवचनम्", 3),
            ("म्", "द्वितीया विभक्तिः (कर्म)", "Accusative (2nd Case)", "Singular / एकवचनम्", 1),
            ("ं", "द्वितीया विभक्तिः (कर्म)", "Accusative (2nd Case)", "Singular / एकवचनम्", 1),
            ("ः", "प्रथमा विभक्तिः (कर्ता)", "Nominative (1st Case)", "Singular / एकवचनम्", 1),
        ]
        for suffix, skt_case, en_case, vacana, trim_len in MODERN_DECLENSIONS:
            if clean_word.endswith(suffix):
                stem = clean_word[:-trim_len]
                if stem in MODERN_SANSKRIT_TERMS:
                    lemma, meaning, category, gender = MODERN_SANSKRIT_TERMS[stem]
                    gloss = MorphologicalGloss(
                        root=lemma,
                        pos="Modern Noun (आधुनिक-संज्ञापदम्)",
                        gender=gender,
                        case=f"{en_case} / {skt_case}",
                        number=vacana,
                        tense=None,
                        person=None,
                        prefix=None,
                        pratyaya=None,
                        voice=None,
                        sanskrit_explanation=f"आधुनिक-संस्कृत-पदम् | मूलम्: {lemma} | अर्थः: {meaning} | {skt_case} | {vacana}",
                        english_explanation=f"Modern Sanskrit term: '{lemma}' ({meaning}) declined in {en_case}, {vacana}.",
                    )
                    return WordAnalysis(word=clean_word, primary_gloss=gloss, confidence=0.98)

        return None

    def _cache_word(self, key: str, analysis: WordAnalysis) -> None:
        """Helper to write to in-memory word cache with LRU eviction."""
        with self._word_cache_lock:
            if len(self._word_cache) >= self._max_token_cache:
                self._word_cache.popitem(last=False)
            self._word_cache[key] = analysis

    def analyze_word(self, word: str) -> WordAnalysis:
        """
        Analyzes a single Sanskrit word token:
        1. Checks in-memory LRU word cache (sub-microsecond resolution for recurring words).
        2. Checks curated NCERT Avyaya dictionary (prevents obscure Vedic nominal collisions like 'api' -> 'ap').
        3. Checks Central Sanskrit University Modern Lexicon (resolves neologisms & modern terms).
        4. Queries Sanskrit Heritage Lexicon with Padānta Sandhi & Upasarga Decomposition.
        5. Ranks and disambiguates valid grammatical interpretations using NCERT syllabus heuristics.
        6. If no lexical tags match, triggers the NCERT Fallback Engine.
        """
        norm_word = SanskritNormalizer.normalize(word)
        clean_word = norm_word.strip("।,॥.?!")
        if not clean_word:
            return self._fallback_analysis(word)

        # 1. Fast path: In-Memory Word LRU Cache
        with self._word_cache_lock:
            if clean_word in self._word_cache:
                self._word_cache.move_to_end(clean_word)
                return self._word_cache[clean_word]

        # 2. NCERT Avyaya check: Prevents rare nominal tags (e.g. 'api' -> water locative) from shadowing indeclinables
        if clean_word in NCERT_AVYAYAS:
            result = self._fallback_analysis(clean_word)
            self._cache_word(clean_word, result)
            return result

        # 3. Modern Sanskrit Lexicon check (Central Sanskrit University neologisms & loanwords)
        modern_analysis = self._lookup_modern_lexicon(clean_word)
        if modern_analysis is not None:
            self._cache_word(clean_word, modern_analysis)
            return modern_analysis

        raw_parses = self._lookup_lexical_database(clean_word)
        if not raw_parses:
            result = self._fallback_analysis(clean_word)
            self._cache_word(clean_word, result)
            return result

        # Convert parses to NCERT glosses
        candidate_glosses: List[MorphologicalGloss] = []
        is_compound_detected = False

        for root_slp1, tag_set, prefix in raw_parses:
            try:
                gloss, is_comp = self._convert_tags_to_gloss(root_slp1, tag_set, clean_word, prefix)
                candidate_glosses.append(gloss)
                if is_comp:
                    is_compound_detected = True
            except Exception as e:
                logger.warning(f"Error parsing tagset {tag_set} for '{word}': {e}")
                continue

        if not candidate_glosses:
            result = self._fallback_analysis(clean_word)
            self._cache_word(clean_word, result)
            return result

        # Disambiguation heuristic for NCERT prose:
        # 1. Finite verbs with Lakāra and Puruṣa rank highest (+150)
        # 2. Participles (Kṛdanta) rank high (+85)
        # 3. True indeclinables (Avyaya) rank high (+80)
        # 4. Pronouns (asmad, yusmad, tad) rank high (+70)
        # 5. Nominative / Accusative nominal cases (+40, +30)
        def _score_gloss(g: MorphologicalGloss) -> int:
            score = 0
            # Common pronouns (अस्मद्, युष्मद्, तद्, यद्, किम्) must NEVER be overshadowed by rare homophonic verbal roots (e.g. मम -> root मा in Liṭ)
            if g.root in ["अस्मद्", "युष्मद्", "तद्", "यद्", "एतद्", "इदम्", "किम्", "भवत्"] or g.pos.startswith("Pronoun"):
                score += 200
            # Indeclinable participles (Ktvā, Lyap, Tumun) are primary non-finite verbal forms in NCERT
            elif g.pratyaya and any(p in g.pratyaya for p in ["तुमुन्", "क्त्वा", "ल्यप्", "Tumun", "Ktvā", "Lyap"]):
                score += 170
            elif g.pos.startswith("Verb") and g.tense and g.person:
                score += 150  # Primary priority: Finite verbs (तिङन्त) are the main predicate in NCERT prose
                # Penalize rare Vedic athematic roots that collide with common -aḥ masculine nouns (e.g. 'रामः' as root 'रा' + 'मः')
                if g.root in ["रा", "मा"] and clean_word.startswith(("राम", "मम")):
                    score -= 100
                elif clean_word.endswith("ः") and not (
                    clean_word.endswith(("तः", "थः", "वः", "ामः", "ेः"))
                    or (clean_word.startswith("अ") and g.tense and "Past" in g.tense)
                ):
                    score -= 80
            elif g.pos.startswith("Noun") or g.pos.startswith("Substantive"):
                score += 110
            elif g.pos.startswith("Participle") or g.pratyaya:
                score += 85
            elif g.pos.startswith("Indeclinable"):
                score += 80

            if g.case:
                if "Nominative" in g.case:
                    score += 40
                elif "Accusative" in g.case:
                    score += 30

            # Prefer active voice for standard textbook prose
            if g.voice and "Active" in g.voice:
                score += 10

            return score

        candidate_glosses.sort(key=_score_gloss, reverse=True)
        primary = candidate_glosses[0]

        # Preserve distinct grammatical cases so syntactic disambiguation and Upapada rules
        # have access to all valid declensional interpretations (not masked by duplicates)
        seen_cases = {primary.case}
        alternatives: List[MorphologicalGloss] = []
        for g in candidate_glosses[1:]:
            if g.case not in seen_cases:
                seen_cases.add(g.case)
                alternatives.append(g)
                if len(alternatives) >= 5:
                    break

        # If room remains, append any other candidate glosses (e.g. different stems/numbers)
        if len(alternatives) < 5:
            for g in candidate_glosses[1:]:
                if g not in alternatives:
                    alternatives.append(g)
                    if len(alternatives) >= 5:
                        break

        result = WordAnalysis(
            word=word,
            primary_gloss=primary,
            alternative_glosses=alternatives,
            is_compound=is_compound_detected,
            confidence=0.96,
        )
        self._cache_word(clean_word, result)
        return result

    def disambiguate_and_extract_karakas(self, analyses: List[WordAnalysis]) -> Tuple[List[WordAnalysis], List[KarakaRelation]]:
        """
        P1 & P2: Contextual Disambiguation, Subject-Verb Agreement, and Upapada-Vibhakti Rules.
        Applies sentence-level Paninian constraints:
        1. Upapada-vibhakti governance: 'सह' forces तृतीया, 'नमः' forces चतुर्थी, 'प्रति' forces द्वितीया, 'बहिः' forces पञ्चमी.
        2. Contextual case disambiguation: If an explicit Nominative (Kartā) exists, ambiguous neuter nominals
           (e.g. पुस्तकम्, फलम्) are promoted to Accusative (Karma / Object).
        3. Subject-Verb agreement (*Kartari prayoga*): Matches nominative subject with finite verb person and number.
        4. Syntactic Kāraka relation graph construction.
        """
        if not analyses:
            return [], []

        # Create cloned instances so we don't mutate cached single-word analyses
        words: List[WordAnalysis] = [
            WordAnalysis(
                word=w.word,
                primary_gloss=w.primary_gloss.model_copy(),
                alternative_glosses=[g.model_copy() for g in w.alternative_glosses],
                is_compound=w.is_compound,
                confidence=w.confidence,
                karaka_role=w.karaka_role,
            )
            for w in analyses
        ]

        karaka_relations: List[KarakaRelation] = []
        n = len(words)

        # ----------------------------------------------------------------------
        # Phase 1: Upapada-Vibhakti Rules (Priority 2)
        # ----------------------------------------------------------------------
        claimed_indices: Set[int] = set()

        for i, item in enumerate(words):
            clean_token = item.word.strip("।,॥.?!")
            if clean_token in UPAPADA_GOVERNORS:
                gov_info = UPAPADA_GOVERNORS[clean_token]
                direction = gov_info["direction"]
                target_idx = None

                if direction in ["prev", "both"] and i > 0:
                    cand = i - 1
                    while cand >= 0 and words[cand].word.strip() in ["।", "॥", ",", "."]:
                        cand -= 1
                    if cand >= 0 and cand not in claimed_indices:
                        target_idx = cand
                elif direction in ["next", "both"] and i < n - 1:
                    cand = i + 1
                    while cand < n and words[cand].word.strip() in ["।", "॥", ",", "."]:
                        cand += 1
                    if cand < n and cand not in claimed_indices:
                        target_idx = cand

                if target_idx is not None:
                    target_word = words[target_idx]
                    req_case_en = gov_info["case_en"]
                    req_vibhakti = gov_info["vibhakti"]
                    allowed_cases = gov_info.get("allowed_cases", [req_case_en, req_vibhakti])

                    # Check if target's primary gloss already matches
                    curr_case = target_word.primary_gloss.case or ""
                    matches_primary = any(c in curr_case for c in allowed_cases)

                    if not matches_primary:
                        # Check alternative glosses for a match
                        match_alt_idx = -1
                        for a_idx, alt_g in enumerate(target_word.alternative_glosses):
                            alt_case = alt_g.case or ""
                            if any(c in alt_case for c in allowed_cases):
                                match_alt_idx = a_idx
                                break
                        if match_alt_idx != -1:
                            # Swap alternative gloss into primary
                            old_prim = target_word.primary_gloss
                            target_word.primary_gloss = target_word.alternative_glosses.pop(match_alt_idx)
                            target_word.alternative_glosses.insert(0, old_prim)
                            matches_primary = True

                    if matches_primary or any(c in (target_word.primary_gloss.case or "") for c in allowed_cases):
                        claimed_indices.add(target_idx)
                        target_word.karaka_role = f"उपपद-सम्बन्धः ({clean_token} योगे {req_vibhakti})"
                        karaka_relations.append(
                            KarakaRelation(
                                source_word=target_word.word,
                                target_word=clean_token,
                                relation=f"उपपद-सम्बन्धः ({clean_token})",
                                vibhakti=req_vibhakti,
                                rule=gov_info["rule"],
                            )
                        )

        # ----------------------------------------------------------------------
        # Phase 2: Contextual Disambiguation & Agreement (Priority 1)
        # ----------------------------------------------------------------------
        # Locate main finite verb or predicative participle
        main_verb_idx = None
        for i, w in enumerate(words):
            if w.primary_gloss.pos.startswith("Verb") and w.primary_gloss.tense:
                main_verb_idx = i
                break

        # Fallback: if no finite verb exists, check for predicative participle (e.g. गतवान्, पठितः, गन्तव्यम्)
        if main_verb_idx is None:
            for i, w in enumerate(words):
                g = w.primary_gloss
                if g.pos.startswith("Participle") or (g.pratyaya and any(p in g.pratyaya for p in ["क्त", "क्तवतु", "तव्यत्", "अनीयर", "Kta", "Ktavatu", "Tavyat", "Anīyar"])):
                    # Ensure it is not an indeclinable gerund (ktva, lyap, tumun)
                    if not any(k in (g.pratyaya or "") for k in ["क्त्वा", "ल्यप्", "तुमुन्", "Ktvā", "Lyap", "Tumun"]):
                        main_verb_idx = i
                        break

        main_verb = words[main_verb_idx] if main_verb_idx is not None else None

        # Identify unambiguous Nominative (Subject)
        subject_idx = None
        unambiguous_subject_tokens = {
            "अहम्", "आवाम्", "वयम्", "त्वम्", "युवाम्", "यूयम्",
            "सः", "सा", "तौ", "ते", "ताः", "एषः", "एषा", "एते",
            "अयम्", "इयम्", "इमे"
        }

        # First pass for explicit pronoun or definite masculine/feminine nominative
        for i, w in enumerate(words):
            if i in claimed_indices or i == main_verb_idx:
                continue
            clean = w.word.strip("।,॥.?!")
            g = w.primary_gloss
            is_explicit_subject = clean in unambiguous_subject_tokens or (
                g.case and "Nominative" in g.case and any(gen in (g.gender or "") for gen in ["Masculine", "Feminine", "पुंल्लिङ्गम्", "स्त्रीलिङ्गम्"])
            )
            if is_explicit_subject:
                subject_idx = i
                w.karaka_role = "कर्ता (Subject)"
                if main_verb:
                    karaka_relations.append(
                        KarakaRelation(
                            source_word=w.word,
                            target_word=main_verb.word,
                            relation="कर्ता (Subject)",
                            vibhakti="प्रथमा",
                            rule="कर्तरि प्रथमा (२.३.४६)",
                        )
                    )
                claimed_indices.add(i)
                break

        # If subject not found yet, take the first Nominative nominal
        if subject_idx is None:
            for i, w in enumerate(words):
                if i in claimed_indices or i == main_verb_idx:
                    continue
                g = w.primary_gloss
                if g.pos in ["Noun", "Pronoun"] or g.pos.startswith("Noun") or g.pos.startswith("Pronoun"):
                    if g.case and "Nominative" in g.case:
                        subject_idx = i
                        w.karaka_role = "कर्ता (Subject)"
                        if main_verb:
                            karaka_relations.append(
                                KarakaRelation(
                                    source_word=w.word,
                                    target_word=main_verb.word,
                                    relation="कर्ता (Subject)",
                                    vibhakti="प्रथमा",
                                    rule="कर्तरि प्रथमा (२.३.४६)",
                                )
                            )
                        claimed_indices.add(i)
                        break

        # Disambiguate remaining nominals (especially Neuter Nom/Acc syncretism & Transitive Objects)
        for i, w in enumerate(words):
            if i in claimed_indices or i == main_verb_idx:
                continue
            clean = w.word.strip("।,॥.?!")
            g = w.primary_gloss
            case_str = g.case or ""

            # Check if this word has an alternative nominal Accusative gloss (e.g. सत्यं when parsed as avyaya)
            if (g.pos.startswith("Indeclinable") or not case_str) and main_verb:
                for a_idx, alt_g in enumerate(w.alternative_glosses):
                    if alt_g.case and "Accusative" in alt_g.case:
                        old_p = w.primary_gloss
                        w.primary_gloss = w.alternative_glosses.pop(a_idx)
                        w.alternative_glosses.insert(0, old_p)
                        g = w.primary_gloss
                        case_str = g.case or ""
                        break

            # Check for Adjective Agreement with Subject or Relative Subject
            if subject_idx is not None and i != subject_idx:
                subj_w = words[subject_idx]
                subj_g = subj_w.primary_gloss
                if g.case and "Nominative" in g.case and subj_g.case and "Nominative" in subj_g.case:
                    # Case A: Relative pronoun (यद्) in complex sentences (यः ... सः)
                    if clean in ["यः", "या", "यत्", "ये"]:
                        w.karaka_role = "कर्ता (Relative Subject)"
                        claimed_indices.add(i)
                        continue
                    # Case B: Adjective agreeing in case, gender, number (विशेषण-विशेष्य भाव)
                    # e.g. दुष्टः राक्षसः, विशालः वटवृक्षः
                    if g.gender and subj_g.gender and g.gender == subj_g.gender and g.number == subj_g.number:
                        w.karaka_role = "विशेषणम् (Subject Modifier)"
                        claimed_indices.add(i)
                        continue

            # If sentence ALREADY has a subject, any second Nom/Acc word (like पुस्तकं, फलम्, सत्यम्) is Accusative (Karma)
            if subject_idx is not None and ("Nominative" in case_str or "Accusative" in case_str or clean in ["सत्यम्", "सत्यं", "पुस्तकम्", "पुस्तकं", "फलम्", "फलं"]):
                # Ensure it has Accusative
                if "Accusative" not in case_str:
                    # Look in alternative glosses for Accusative
                    for a_idx, alt_g in enumerate(w.alternative_glosses):
                        if alt_g.case and "Accusative" in alt_g.case:
                            old_p = w.primary_gloss
                            w.primary_gloss = w.alternative_glosses.pop(a_idx)
                            w.alternative_glosses.insert(0, old_p)
                            case_str = w.primary_gloss.case or ""
                            break
                    else:
                        # Convert to Accusative directly for neuter/common nouns
                        w.primary_gloss.case = "द्वितीया विभक्तिः (कर्म), Accusative (2nd Case)"

                # Neuter normalization for canonical neuter words
                if clean in ["पुस्तकम्", "पुस्तकं", "फलम्", "फलं", "सत्यम्", "सत्यं", "जलम्", "जलं", "गृहम्", "गृहं", "पत्रम्", "पत्रं", "मित्रम्", "मित्रं"]:
                    w.primary_gloss.gender = "Neuter / नपुंसकलिङ्गम्"

                w.karaka_role = "कर्म (Direct Object)"
                claimed_indices.add(i)
                if main_verb:
                    karaka_relations.append(
                        KarakaRelation(
                            source_word=w.word,
                            target_word=main_verb.word,
                            relation="कर्म (Object)",
                            vibhakti="द्वितीया",
                            rule="कर्मणि द्वितीया (२.३.२)",
                        )
                    )
            elif "Accusative" in case_str:
                w.karaka_role = "कर्म (Direct Object)"
                claimed_indices.add(i)
                if main_verb:
                    karaka_relations.append(
                        KarakaRelation(
                            source_word=w.word,
                            target_word=main_verb.word,
                            relation="कर्म (Object)",
                            vibhakti="द्वितीया",
                            rule="कर्मणि द्वितीया (२.३.२)",
                        )
                    )
            elif "Instrumental" in case_str:
                w.karaka_role = "करणम् (Instrument)"
                claimed_indices.add(i)
                if main_verb:
                    karaka_relations.append(
                        KarakaRelation(
                            source_word=w.word,
                            target_word=main_verb.word,
                            relation="करणम् (Instrument)",
                            vibhakti="तृतीया",
                            rule="कर्तृकरणयोस्तृतीया (२.३.१८)",
                        )
                    )
            elif "Dative" in case_str:
                w.karaka_role = "सम्प्रदानम् (Recipient)"
                claimed_indices.add(i)
                if main_verb:
                    karaka_relations.append(
                        KarakaRelation(
                            source_word=w.word,
                            target_word=main_verb.word,
                            relation="सम्प्रदानम् (Recipient)",
                            vibhakti="चतुर्थी",
                            rule="चतुर्थी सम्प्रदाने (२.३.१३)",
                        )
                    )
            elif "Ablative" in case_str:
                w.karaka_role = "अपादानम् (Source)"
                claimed_indices.add(i)
                if main_verb:
                    karaka_relations.append(
                        KarakaRelation(
                            source_word=w.word,
                            target_word=main_verb.word,
                            relation="अपादानम् (Source)",
                            vibhakti="पञ्चमी",
                            rule="अपादाने पञ्चमी (२.३.२८)",
                        )
                    )
            elif "Genitive" in case_str:
                w.karaka_role = "सम्बन्धः (Possessive)"
                claimed_indices.add(i)
                target_noun = words[i+1].word if i+1 < n else (main_verb.word if main_verb else "")
                karaka_relations.append(
                    KarakaRelation(
                        source_word=w.word,
                        target_word=target_noun,
                        relation="सम्बन्धः (Possessive)",
                        vibhakti="षष्ठी",
                        rule="षष्ठी शेषे (२.३.५०)",
                    )
                )
            elif "Locative" in case_str:
                w.karaka_role = "अधिकरणम् (Location)"
                claimed_indices.add(i)
                if main_verb:
                    karaka_relations.append(
                        KarakaRelation(
                            source_word=w.word,
                            target_word=main_verb.word,
                            relation="अधिकरणम् (Location)",
                            vibhakti="सप्तमी",
                            rule="सप्तम्यधिकरणे च (२.३.३६)",
                        )
                    )
            elif g.pratyaya and any(k in g.pratyaya for k in ["ktvA", "lyap", "Ktvā", "Lyap", "क्त्वा", "ल्यप्"]):
                w.karaka_role = "पूर्वकालिक-क्रिया (Participle)"
                claimed_indices.add(i)
                if main_verb and main_verb != w:
                    karaka_relations.append(
                        KarakaRelation(
                            source_word=w.word,
                            target_word=main_verb.word,
                            relation="पूर्वकालिक-क्रिया",
                            vibhakti="कृदन्त",
                            rule="समानकर्तृकयोः पूर्वकाले (३.४.२१)",
                        )
                    )
            elif g.pratyaya and any(k in g.pratyaya for k in ["tumun", "Tumun", "तुमुन्"]):
                w.karaka_role = "प्रयोजनम् (Infinitive of Purpose)"
                claimed_indices.add(i)
                if main_verb and main_verb != w:
                    karaka_relations.append(
                        KarakaRelation(
                            source_word=w.word,
                            target_word=main_verb.word,
                            relation="प्रयोजनम्",
                            vibhakti="तुमुन्",
                            rule="तुमुन्ण्वुलौ क्रियायां क्रियार्थायाम् (३.३.१०)",
                        )
                    )
            elif g.pratyaya and any(k in g.pratyaya for k in ["Satf", "Śatṛ", "शतृ", "Sanac", "Śānac", "शानच्"]):
                w.karaka_role = "समानाधिकरण-विशेषणम् (Participle)"
                claimed_indices.add(i)
                if main_verb and main_verb != w:
                    karaka_relations.append(
                        KarakaRelation(
                            source_word=w.word,
                            target_word=main_verb.word,
                            relation="समानाधिकरण-विशेषणम्",
                            vibhakti="शतृ/शानच्",
                            rule="लक्षणहेत्वोः क्रियायाः (३.२.१२६)",
                        )
                    )

        if main_verb and not main_verb.karaka_role:
            if main_verb.primary_gloss.pos.startswith("Participle"):
                main_verb.karaka_role = "विधेय-कृदन्तम् (Predicative Participle)"
            else:
                main_verb.karaka_role = "क्रियापदम् (Finite Verb)"

        return words, karaka_relations

    def analyze_tokens(self, tokens: List[str]) -> List[WordAnalysis]:
        """Analyzes a sequence of sandhi-split tokens with contextual disambiguation and Upapada rules."""
        raw_analyses = [self.analyze_word(token) for token in tokens if token.strip()]
        disambiguated, _ = self.disambiguate_and_extract_karakas(raw_analyses)
        return disambiguated

_global_morphology_service: Optional[MorphologyService] = None
_global_morphology_lock = threading.Lock()

def get_morphology_service() -> MorphologyService:
    """Provides application-wide singleton MorphologyService instance."""
    global _global_morphology_service
    if _global_morphology_service is None:
        with _global_morphology_lock:
            if _global_morphology_service is None:
                _global_morphology_service = MorphologyService()
    return _global_morphology_service
