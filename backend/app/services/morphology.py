import re
import logging
from typing import List, Optional, Set, Tuple, Dict, Any

from indic_transliteration import sanscript
from sanskrit_parser.base.sanskrit_base import SanskritNormalizedString
from sanskrit_parser.parser.sandhi_analyzer import LexicalSandhiAnalyzer

from app.models.schemas import MorphologicalGloss, WordAnalysis

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
    "tva": ("त्व प्रत्ययः", "Tva (abstract noun suffix)"),
    "tal": ("तल् प्रत्ययः", "Tal (abstract noun suffix)"),
}

PRAYOGA_MAP: Dict[str, Tuple[str, str]] = {
    "kartari": ("कर्तरि प्रयोगः", "Active Voice"),
    "karmaNi": ("कर्मणि प्रयोगः", "Passive Voice"),
    "BAve": ("भावे प्रयोगः", "Impersonal Voice"),
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
}

# Suffix patterns for Kṛdanta (Participles) fallback
# (suffix, pratyaya_key, pos_label, trim_len)
KRDANTA_PATTERNS: List[Tuple[str, str, str, int]] = [
    ("इत्वा", "ktvA", "Participle (कृदन्तपदम्)", 4),
    ("त्वा", "ktvA", "Participle (कृदन्तपदम्)", 3),
    ("ितुम्", "tumun", "Participle (कृदन्तपदम्)", 4),
    ("तुम्", "tumun", "Participle (कृदन्तपदम्)", 3),
    ("ष्टुम्", "tumun", "Participle (कृदन्तपदम्)", 4),
    ("ितवान्", "ktavatu", "Participle (कृदन्तपदम्)", 5),
    ("तवान्", "ktavatu", "Participle (कृदन्तपदम्)", 4),
    ("ितवती", "ktavatu", "Participle (कृदन्तपदम्)", 5),
    ("तवती", "ktavatu", "Participle (कृदन्तपदम्)", 4),
    ("ितवत्", "ktavatu", "Participle (कृदन्तपदम्)", 5),
    ("तवत्", "ktavatu", "Participle (कृदन्तपदम्)", 4),
    ("ितव्यम्", "tavya", "Participle (कृदन्तपदम्)", 6),
    ("तव्यम्", "tavya", "Participle (कृदन्तपदम्)", 5),
    ("ितव्यः", "tavya", "Participle (कृदन्तपदम्)", 6),
    ("तव्यः", "tavya", "Participle (कृदन्तपदम्)", 5),
    ("ितव्या", "tavya", "Participle (कृदन्तपदम्)", 6),
    ("तव्या", "tavya", "Participle (कृदन्तपदम्)", 5),
    ("नीयम्", "anIya", "Participle (कृदन्तपदम्)", 4),
    ("नीयः", "anIya", "Participle (कृदन्तपदम्)", 4),
    ("नीया", "anIya", "Participle (कृदन्तपदम्)", 4),
    ("ितः", "kta", "Participle (कृदन्तपदम्)", 3),
    ("तः", "kta", "Participle (कृदन्तपदम्)", 2),
    ("िता", "kta", "Participle (कृदन्तपदम्)", 3),
    ("ता", "kta", "Participle (कृदन्तपदम्)", 2),
    ("ितम्", "kta", "Participle (कृदन्तपदम्)", 4),
    ("तम्", "kta", "Participle (कृदन्तपदम्)", 3),
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

    # 4. Present Tense (Laṭ - लट्)
    ("न्ति", "law", "praTamapuruzaH", "bahuvacanam", 3),
    ("थः", "law", "maDyamapuruzaH", "dvivacanam", 2),
    ("तः", "law", "praTamapuruzaH", "dvivacanam", 2),
    ("ति", "law", "praTamapuruzaH", "ekavacanam", 2),
    ("सि", "law", "maDyamapuruzaH", "ekavacanam", 2),
    ("थ", "law", "maDyamapuruzaH", "bahuvacanam", 1),
    ("मि", "law", "uttamapuruzaH", "ekavacanam", 2),
    ("वः", "law", "uttamapuruzaH", "dvivacanam", 2),
    ("मः", "law", "uttamapuruzaH", "bahuvacanam", 2),

    # Present Tense Ātmanepada (लट् आत्मनेपदम्)
    ("न्ते", "law", "praTamapuruzaH", "bahuvacanam", 3),
    ("ते", "law", "praTamapuruzaH", "ekavacanam", 2),
    ("से", "law", "maDyamapuruzaH", "ekavacanam", 2),
    ("महे", "law", "uttamapuruzaH", "bahuvacanam", 2),
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
    # Dual 1st/2nd -au
    ("ौ", "praTamAviBaktiH", "dvivacanam", "puMlliNgam", 1),
    # 7th singular -e
    ("े", "saptamIviBaktiH", "ekavacanam", "napuMsakaliNgam", 1),
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
    Kṛdanta participle mapping, and deterministic Paninian rule fallbacks
    to provide zero-stub, pedagogical grammatical tagging.
    """

    def __init__(self):
        self._analyzer = LexicalSandhiAnalyzer()

    @staticmethod
    def _devanagari_to_slp1(devanagari_text: str) -> str:
        """Converts Devanagari text to SLP1 encoding."""
        return sanscript.transliterate(devanagari_text, sanscript.DEVANAGARI, sanscript.SLP1)

    @staticmethod
    def _slp1_to_devanagari(slp1_text: Any) -> str:
        """Converts SLP1 transliterated root or token to Devanagari."""
        clean_slp1 = re.sub(r"#\d+", "", str(slp1_text)).strip()
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

        # If Heritage tagged avyayaDAturUpa without explicit pratyaya, infer from surface
        if is_participle and not pratyaya_val:
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

        # 3. Check General Kṛdanta Participle Patterns (Ktvā, Tumun, Ktavatu, Kta, Tavyat, Anīyar)
        for suffix, pratyaya_key, pos_label, trim_len in KRDANTA_PATTERNS:
            if clean.endswith(suffix):
                stem = clean[:-trim_len]
                root_raw = DHATU_CANONICAL.get(stem, stem + "्" if stem else clean)
                prat_val = f"{PRATYAYA_MAP[pratyaya_key][0]} / {PRATYAYA_MAP[pratyaya_key][1]}"

                # Gender/case details for declined participles
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
                else:
                    skt_exp = f"मूलधातुः: {root_raw} | {PRATYAYA_MAP[pratyaya_key][0]} (कृदन्त अव्ययपदम्)"
                    eng_exp = f"Root: '{root_raw}', Indeclinable participle formed with {PRATYAYA_MAP[pratyaya_key][1]}."

                gloss = MorphologicalGloss(
                    root=root_raw,
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

        # 4. Check Past Imperfect Tense (Laṅ - लङ्) with initial 'a-' augment
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

        # 5. Check Tiṅanta (Verb) Suffix Patterns for other Lakāras (Lṛṭ, Loṭ, Vidhiliṅ, Laṭ)
        for suffix, lakara_key, purusha_key, vacana_key, trim_len in TINANTA_PATTERNS:
            if clean.endswith(suffix):
                stem = clean[:-trim_len]
                root_raw = DHATU_CANONICAL.get(stem, stem + "्" if stem else clean)
                tense_val = f"{LAKARA_MAP[lakara_key][1]} / {LAKARA_MAP[lakara_key][0]}"
                person_val = f"{PURUSHA_MAP[purusha_key][1]} / {PURUSHA_MAP[purusha_key][0]}"
                vacana_val = f"{VACANA_MAP[vacana_key][1]} / {VACANA_MAP[vacana_key][0]}"
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
                    sanskrit_explanation=f"धातुः: {root_raw} | {LAKARA_MAP[lakara_key][0]} | {PURUSHA_MAP[purusha_key][0]} | {VACANA_MAP[vacana_key][0]} | कर्तरि प्रयोगः",
                    english_explanation=f"Root: '{root_raw}', Verb conjugated in {LAKARA_MAP[lakara_key][1]}, {PURUSHA_MAP[purusha_key][1]}, {VACANA_MAP[vacana_key][1]} (Active Voice).",
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

    def analyze_word(self, word: str) -> WordAnalysis:
        """
        Analyzes a single Sanskrit word token:
        1. Checks curated NCERT Avyaya dictionary (prevents obscure Vedic nominal collisions like 'api' -> 'ap').
        2. Queries Sanskrit Heritage Lexicon with Padānta Sandhi & Upasarga Decomposition.
        3. Ranks and disambiguates valid grammatical interpretations using NCERT syllabus heuristics.
        4. If no lexical tags match, triggers the NCERT Fallback Engine.
        """
        clean_word = word.strip("।,॥.?!")
        if not clean_word:
            return self._fallback_analysis(word)

        # 1. NCERT Avyaya check: Prevents rare nominal tags (e.g. 'api' -> water locative) from shadowing indeclinables
        if clean_word in NCERT_AVYAYAS:
            return self._fallback_analysis(clean_word)

        raw_parses = self._lookup_lexical_database(clean_word)
        if not raw_parses:
            return self._fallback_analysis(clean_word)

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
            return self._fallback_analysis(clean_word)

        # Disambiguation heuristic for NCERT prose:
        # 1. Finite verbs with Lakāra and Puruṣa rank highest (+100)
        # 2. Participles (Kṛdanta) rank high (+85)
        # 3. True indeclinables (Avyaya) rank high (+80)
        # 4. Pronouns (asmad, yusmad, tad) rank high (+70)
        # 5. Nominative / Accusative nominal cases (+40, +30)
        def _score_gloss(g: MorphologicalGloss) -> int:
            score = 0
            if g.pos.startswith("Verb") and g.tense and g.person:
                score += 150  # Primary priority: Finite verbs (तिङन्त) are the main predicate in NCERT prose
            elif g.pos.startswith("Participle") or g.pratyaya:
                score += 85
            elif g.pos.startswith("Indeclinable"):
                score += 80
            elif g.pos.startswith("Pronoun"):
                score += 70

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
        alternatives = candidate_glosses[1:4]  # Keep up to 3 relevant alternatives

        return WordAnalysis(
            word=word,
            primary_gloss=primary,
            alternative_glosses=alternatives,
            is_compound=is_compound_detected,
            confidence=0.96,
        )

    def analyze_tokens(self, tokens: List[str]) -> List[WordAnalysis]:
        """Analyzes a sequence of sandhi-split tokens."""
        return [self.analyze_word(token) for token in tokens if token.strip()]
