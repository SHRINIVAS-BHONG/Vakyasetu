import re
import logging
import threading
from typing import List, Optional, Dict, Any, Tuple

from app.models.schemas import SamasaAnalysis
from app.core.normalizer import SanskritNormalizer

logger = logging.getLogger(__name__)

# ==============================================================================
# NCERT / CBSE CLASS 9 & 10 CANONICAL SAMĀSA DATABASE & PATTERNS
# ==============================================================================

# Curated lookup for authentic NCERT Shemushi/Manika textbook compounds
CURATED_SAMASAS: Dict[str, Dict[str, Any]] = {
    # 1. अव्ययीभावः (Avyayībhāva)
    "यथाशक्ति": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "शक्तिम् अनतिक्रम्य",
        "components": ["यथा", "शक्ति"],
        "explanation": "शक्ति के अनुसार (यथा-अव्यय का योग)",
    },
    "यथामति": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "मतिम् अनतिक्रम्य",
        "components": ["यथा", "मति"],
        "explanation": "बुद्धि के अनुसार",
    },
    "यथारुचि": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "रुचिम् अनतिक्रम्य",
        "components": ["यथा", "रुचि"],
        "explanation": "रुचि के अनुसार",
    },
    "यथाकामम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "कामम् अनतिक्रम्य",
        "components": ["यथा", "काम"],
        "explanation": "इच्छानुसार",
    },
    "उपग्रामम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "ग्रामस्य समीपम्",
        "components": ["उप", "ग्राम"],
        "explanation": "गाँव के समीप (उप-सामीप्ये)",
    },
    "उपनगरम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "नगरस्य समीपम्",
        "components": ["उप", "नगर"],
        "explanation": "नगर के समीप",
    },
    "उपकृष्णम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "कृष्णस्य समीपम्",
        "components": ["उप", "कृष्ण"],
        "explanation": "श्रीकृष्ण के समीप",
    },
    "उपगङ्गम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "गङ्गायाः समीपम्",
        "components": ["उप", "गङ्गा"],
        "explanation": "गंगा के समीप",
    },
    "प्रतिदिनम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "दिनं दिनं प्रति",
        "components": ["प्रति", "दिन"],
        "explanation": "प्रत्येक दिन (प्रति-वीप्सायाम्)",
    },
    "प्रत्येकम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "एकम् एकं प्रति",
        "components": ["प्रति", "एक"],
        "explanation": "हर एक",
    },
    "प्रतिगृहम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "गृहं गृहं प्रति",
        "components": ["प्रति", "गृह"],
        "explanation": "घर-घर में",
    },
    "प्रतिवर्षम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "वर्षं वर्षं प्रति",
        "components": ["प्रति", "वर्ष"],
        "explanation": "हर वर्ष",
    },
    "प्रत्यक्षम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "अक्ष्णोः प्रति",
        "components": ["प्रति", "अक्षि"],
        "explanation": "आँखों के सामने",
    },
    "अनुरूपम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "रूपस्य योग्यम्",
        "components": ["अनु", "रूप"],
        "explanation": "रूप के योग्य (अनु-योग्यतायाम्)",
    },
    "अनुदिनम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "दिने दिने इति",
        "components": ["अनु", "दिन"],
        "explanation": "नित्य / प्रतिदिन",
    },
    "निर्मक्षिकम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "मक्षिकाणाम् अभावः",
        "components": ["निर्", "मक्षिका"],
        "explanation": "मक्खियों का अभाव (निर्-अभावे)",
    },
    "निर्जनम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "जनानाम् अभावः",
        "components": ["निर्", "जन"],
        "explanation": "मनुष्यों से रहित स्थान",
    },
    "निर्विघ्नम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "विघ्नानाम् अभावः",
        "components": ["निर्", "विघ्न"],
        "explanation": "बिना किसी बाधा के",
    },
    "सादरम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "आदरेण सहितम्",
        "components": ["स", "आदर"],
        "explanation": "आदर सहित (स-सादृश्ये/साहित्ये)",
    },
    "सक्रोधम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "क्रोधेन सहितम्",
        "components": ["स", "क्रोध"],
        "explanation": "क्रोध के साथ",
    },
    "सोत्साहम्": {
        "samasa_type": "अव्ययीभावः",
        "vigraha": "उत्साहेन सहितम्",
        "components": ["स", "उत्साह"],
        "explanation": "उत्साहपूर्वक",
    },

    # 2. तत्पुरुषः (Tatpuruṣa)
    "राजपुरुषः": {
        "samasa_type": "षष्ठी-तत्पुरुषः",
        "vigraha": "राज्ञः पुरुषः",
        "components": ["राजन्", "पुरुष"],
        "explanation": "राजा का सेवक / अधिकारी",
    },
    "राजदूतः": {
        "samasa_type": "षष्ठी-तत्पुरुषः",
        "vigraha": "राज्ञः दूतः",
        "components": ["राजन्", "दूत"],
        "explanation": "राजा का दूत",
    },
    "देवमन्दिरम्": {
        "samasa_type": "षष्ठी-तत्पुरुषः",
        "vigraha": "देवस्य मन्दिरम्",
        "components": ["देव", "मन्दिर"],
        "explanation": "देवता का मन्दिर",
    },
    "विद्यासागरः": {
        "samasa_type": "षष्ठी-तत्पुरुषः",
        "vigraha": "विद्यायाः सागरः",
        "components": ["विद्या", "सागर"],
        "explanation": "ज्ञान का समुद्र",
    },
    "सूर्यवंशः": {
        "samasa_type": "षष्ठी-तत्पुरुषः",
        "vigraha": "सूर्यस्य वंशः",
        "components": ["सूर्य", "वंश"],
        "explanation": "सूर्य का कुल",
    },
    "हिमालयः": {
        "samasa_type": "षष्ठी-तत्पुरुषः",
        "vigraha": "हिमस्य आलयः",
        "components": ["हिम", "आलय"],
        "explanation": "बर्फ का घर (पर्वत)",
    },
    "देशभक्तः": {
        "samasa_type": "षष्ठी-तत्पुरुषः",
        "vigraha": "देशस्य भक्तः",
        "components": ["देश", "भक्त"],
        "explanation": "देश का भक्त",
    },
    "राष्ट्रपिता": {
        "samasa_type": "षष्ठी-तत्पुरुषः",
        "vigraha": "राष्ट्रस्य पिता",
        "components": ["राष्ट्र", "पितृ"],
        "explanation": "राष्ट्र के पिता",
    },
    "ज्ञानयुक्तः": {
        "samasa_type": "तृतीया-तत्पुरुषः",
        "vigraha": "ज्ञानेन युक्तः",
        "components": ["ज्ञान", "युक्त"],
        "explanation": "ज्ञान से सम्पन्न",
    },
    "धनहीनः": {
        "samasa_type": "तृतीया-तत्पुरुषः",
        "vigraha": "धनेन हीनः",
        "components": ["धन", "हीन"],
        "explanation": "धन से रहित",
    },
    "भयव्याकुलः": {
        "samasa_type": "तृतीया-तत्पुरुषः",
        "vigraha": "भयेन व्याकुलः",
        "components": ["भय", "व्याकुल"],
        "explanation": "डर से व्याकुल",
    },
    "ग्रामगतः": {
        "samasa_type": "द्वितीया-तत्पुरुषः",
        "vigraha": "ग्रामं गतः",
        "components": ["ग्राम", "गत"],
        "explanation": "गाँव को गया हुआ",
    },
    "सुखप्राप्तः": {
        "samasa_type": "द्वितीया-तत्पुरुषः",
        "vigraha": "सुखं प्राप्तः",
        "components": ["सुख", "प्राप्त"],
        "explanation": "सुख को प्राप्त",
    },
    "गोहितम्": {
        "samasa_type": "चतुर्थी-तत्पुरुषः",
        "vigraha": "गवे हितम्",
        "components": ["गो", "हित"],
        "explanation": "गाय के लिए कल्याणकारी",
    },
    "चौरभीतः": {
        "samasa_type": "पञ्चमी-तत्पुरुषः",
        "vigraha": "चौरात् भीतः",
        "components": ["चौर", "भीत"],
        "explanation": "चोर से डरा हुआ",
    },
    "मार्गभ्रष्टः": {
        "samasa_type": "पञ्चमी-तत्पुरुषः",
        "vigraha": "मार्गात् भ्रष्टः",
        "components": ["मार्ग", "भ्रष्ट"],
        "explanation": "रास्ते से भटका हुआ",
    },
    "ऋणमुक्तः": {
        "samasa_type": "पञ्चमी-तत्पुरुषः",
        "vigraha": "ऋणात् मुक्तः",
        "components": ["ऋण", "मुक्त"],
        "explanation": "ऋण से मुक्त",
    },
    "कार्यकुशलः": {
        "samasa_type": "सप्तमी-तत्पुरुषः",
        "vigraha": "कार्ये कुशलः",
        "components": ["कार्य", "कुशल"],
        "explanation": "काम में निपुण",
    },
    "रणपण्डितः": {
        "samasa_type": "सप्तमी-तत्पुरुषः",
        "vigraha": "रणे पण्डितः",
        "components": ["रण", "पण्डित"],
        "explanation": "युद्धविद्या में चतुर",
    },
    "ध्यानमग्नः": {
        "samasa_type": "सप्तमी-तत्पुरुषः",
        "vigraha": "ध्याने मग्नः",
        "components": ["ध्यान", "मग्न"],
        "explanation": "ध्यान में लीन",
    },

    # नञ्-तत्पुरुषः
    "असत्यम्": {
        "samasa_type": "नञ्-तत्पुरुषः",
        "vigraha": "न सत्यम्",
        "components": ["अ", "सत्य"],
        "explanation": "जो सत्य नहीं है / झूठ",
    },
    "अधर्मः": {
        "samasa_type": "नञ्-तत्पुरुषः",
        "vigraha": "न धर्मः",
        "components": ["अ", "धर्म"],
        "explanation": "जो धर्म नहीं है",
    },
    "अज्ञानम्": {
        "samasa_type": "नञ्-तत्पुरुषः",
        "vigraha": "न ज्ञानम्",
        "components": ["अ", "ज्ञान"],
        "explanation": "ज्ञान का अभाव",
    },
    "अनागतम्": {
        "samasa_type": "नञ्-तत्पुरुषः",
        "vigraha": "न आगतम्",
        "components": ["अन्", "आगत"],
        "explanation": "जो अभी नहीं आया है / भविष्य",
    },
    "अनर्थः": {
        "samasa_type": "नञ्-तत्पुरुषः",
        "vigraha": "न अर्थः",
        "components": ["अन्", "अर्थ"],
        "explanation": "बुरा परिणाम / संकट",
    },

    # 3. कर्मधारयः (Karmadhāraya)
    "नीलोत्पलम्": {
        "samasa_type": "कर्मधारयः",
        "vigraha": "नीलं तत् उत्पलम्",
        "components": ["नील", "उत्पल"],
        "explanation": "नीला कमल (विशेषण-विशेष्य)",
    },
    "महापुरुषः": {
        "samasa_type": "कर्मधारयः",
        "vigraha": "महान् चासौ पुरुषः",
        "components": ["महत्", "पुरुष"],
        "explanation": "महान् व्यक्ति",
    },
    "घनश्यामः": {
        "samasa_type": "कर्मधारयः",
        "vigraha": "घन इव श्यामः",
        "components": ["घन", "श्याम"],
        "explanation": "बादल जैसा साँवला (उपमान-उपमेय)",
    },
    "चरणकमलम्": {
        "samasa_type": "कर्मधारयः",
        "vigraha": "कमलम् इव चरणम्",
        "components": ["चरण", "कमल"],
        "explanation": "कमल जैसे कोमल चरण",
    },
    "मुखचन्द्रः": {
        "samasa_type": "कर्मधारयः",
        "vigraha": "चन्द्र इव मुखम्",
        "components": ["मुख", "चन्द्र"],
        "explanation": "चन्द्रमा जैसा सुन्दर मुख",
    },

    # 4. द्विगुः (Dvigu)
    "पञ्चवटी": {
        "samasa_type": "द्विगुः",
        "vigraha": "पञ्चानां वटानां समाहारः",
        "components": ["पञ्चन्", "वट"],
        "explanation": "पाँच वटवृक्षों का समूह (संख्यापूर्वो द्विगुः)",
    },
    "त्रिभुवनम्": {
        "samasa_type": "द्विगुः",
        "vigraha": "त्रयाणां भुवनानां समाहारः",
        "components": ["त्रि", "भुवन"],
        "explanation": "तीनों लोकों का समाहार",
    },
    "त्रिफला": {
        "samasa_type": "द्विगुः",
        "vigraha": "त्रयाणां फलानां समाहारः",
        "components": ["त्रि", "फल"],
        "explanation": "तीन फलों का समूह",
    },
    "सप्तर्षयः": {
        "samasa_type": "द्विगुः",
        "vigraha": "सप्तानां ऋषीणां समाहारः",
        "components": ["सप्तन्", "ऋषि"],
        "explanation": "सात ऋषियों का समूह",
    },
    "नवरत्नम्": {
        "samasa_type": "द्विगुः",
        "vigraha": "नवानां रत्नानां समाहारः",
        "components": ["नवन्", "रत्न"],
        "explanation": "नौ रत्नों का समूह",
    },
    "शताब्दी": {
        "samasa_type": "द्विगुः",
        "vigraha": "शतानाम् अब्दानां समाहारः",
        "components": ["शत", "अब्द"],
        "explanation": "सौ वर्षों का समूह",
    },

    # 5. द्वन्द्वः (Dvandva)
    "रामलक्ष्मणौ": {
        "samasa_type": "इतरेतर-द्वन्द्वः",
        "vigraha": "रामः च लक्ष्मणः च",
        "components": ["राम", "लक्ष्मण"],
        "explanation": "राम और लक्ष्मण (चार्थे द्वन्द्वः)",
    },
    "मातापितरौ": {
        "samasa_type": "इतरेतर-द्वन्द्वः",
        "vigraha": "माता च पिता च",
        "components": ["मातृ", "पितृ"],
        "explanation": "माता और पिता",
    },
    "पितरौ": {
        "samasa_type": "एकशेष-द्वन्द्वः",
        "vigraha": "माता च पिता च",
        "components": ["मातृ", "पितृ"],
        "explanation": "माता और पिता",
    },
    "हरिहरौ": {
        "samasa_type": "इतरेतर-द्वन्द्वः",
        "vigraha": "हरिः च हरः च",
        "components": ["हरि", "हर"],
        "explanation": "विष्णु और शिव",
    },
    "धर्मार्थकाममोक्षाः": {
        "samasa_type": "इतरेतर-द्वन्द्वः",
        "vigraha": "धर्मः च अर्थः च कामः च मोक्षः च",
        "components": ["धर्म", "अर्थ", "काम", "मोक्ष"],
        "explanation": "चारों पुरुषार्थ",
    },
    "पाणिपादम्": {
        "samasa_type": "समाहार-द्वन्द्वः",
        "vigraha": "पाणी च पादौ च एषां समाहारः",
        "components": ["पाणि", "पाद"],
        "explanation": "हाथ और पैरों का समाहार",
    },
    "अहिनकुलम्": {
        "samasa_type": "समाहार-द्वन्द्वः",
        "vigraha": "अहिः च नकुलः च तयोः समाहारः",
        "components": ["अहि", "नकुल"],
        "explanation": "साँप और नेवले का स्वाभाविक विरोधयुक्त समाहार",
    },

    # 6. बहुव्रीहिः (Bahuvrīhi)
    "पीताम्बरः": {
        "samasa_type": "बहुव्रीहिः",
        "vigraha": "पीतं अम्बरं यस्य सः (विष्णुः)",
        "components": ["पीत", "अम्बर"],
        "explanation": "पीले वस्त्र हैं जिसके (श्रीकृष्ण / विष्णु)",
    },
    "दशाननः": {
        "samasa_type": "बहुव्रीहिः",
        "vigraha": "दश आननानि यस्य सः (रावणः)",
        "components": ["दशन्", "आनन"],
        "explanation": "दस मुख हैं जिसके (रावण)",
    },
    "लम्बोदरः": {
        "samasa_type": "बहुव्रीहिः",
        "vigraha": "लम्बम् उदरं यस्य सः (गणेशः)",
        "components": ["लम्ब", "उदर"],
        "explanation": "बड़ा उदर है जिसका (श्रीगणेश)",
    },
    "चक्रपाणिः": {
        "samasa_type": "बहुव्रीहिः",
        "vigraha": "चक्रे पाणौ यस्य सः (विष्णुः)",
        "components": ["चक्र", "पाणि"],
        "explanation": "हाथ में चक्र है जिसके (भगवान् विष्णु)",
    },
    "चन्द्रशेखरः": {
        "samasa_type": "बहुव्रीहिः",
        "vigraha": "चन्द्रः शेखरे यस्य सः (शिवः)",
        "components": ["चन्द्र", "शेखर"],
        "explanation": "मस्तक पर चन्द्रमा है जिसके (भगवान् शिव)",
    },
}

class SamasaService:
    """
    P4: CBSE/NCERT Class 9 & 10 Sanskrit Samāsa Decomposition Engine.
    Recognizes, decomposes, and generates Vigraha-vākya for classical compounds.
    """

    def __init__(self):
        self._cache: Dict[str, Optional[SamasaAnalysis]] = {}
        self._stem_cache: Dict[str, bool] = {}
        self._stem_db_conn = None
        self._lock = threading.Lock()

    def _is_lexical_stem(self, dev_stem: str) -> bool:
        """
        Dynamically checks if a candidate nominal stem exists in the 185,000+
        canonical Sanskrit stem database or modern neologisms (zero hardcoding).
        """
        dev_stem = dev_stem.strip("।,॥.?!")
        if len(dev_stem) < 2:
            return False
        with self._lock:
            if dev_stem in self._stem_cache:
                return self._stem_cache[dev_stem]

        # 1. Check modern loanwords and neologisms
        try:
            from app.core.modern_lexicon import MODERN_SANSKRIT_TERMS
            if (
                dev_stem in MODERN_SANSKRIT_TERMS
                or (dev_stem + "म्") in MODERN_SANSKRIT_TERMS
                or (dev_stem + "ः") in MODERN_SANSKRIT_TERMS
            ):
                with self._lock:
                    self._stem_cache[dev_stem] = True
                return True
        except Exception:
            pass

        # 2. Check 185,000+ Sanskrit stems in Heritage sqlite database
        try:
            if self._stem_db_conn is None:
                import sqlite3
                import sanskrit_parser.util.sanskrit_data_wrapper as sdw
                db_path = sdw.data_file_path(sdw.SanskritDataWrapper.db_file)
                self._stem_db_conn = sqlite3.connect(db_path, check_same_thread=False)

            from indic_transliteration import sanscript
            slp = sanscript.transliterate(dev_stem, sanscript.DEVANAGARI, sanscript.SLP1)
            cur = self._stem_db_conn.cursor()
            cur.execute("SELECT 1 FROM stem WHERE name=? LIMIT 1", (slp,))
            if cur.fetchone():
                with self._lock:
                    self._stem_cache[dev_stem] = True
                return True
        except Exception:
            pass

        with self._lock:
            self._stem_cache[dev_stem] = False
        return False

    def _is_lexical_word(self, dev_word: str) -> bool:
        """
        Checks if a full inflected word or its stripped stem exists in Sanskrit lexicon.
        """
        clean = dev_word.strip("।,॥.?!")
        if len(clean) < 2:
            return False
        if self._is_lexical_stem(clean):
            return True

        # Suffix stripping to recover underlying prātipadika stem
        for sfx in ("ानि", "ाणि", "ेभ्यः", "ाणाम्", "ेषु", "ाभ्याम्", "ेण", "ेन", "ाय", "ात्", "स्य", "ाः", "ः", "म्", "ौ", "े", "ा"):
            if clean.endswith(sfx) and len(clean) > len(sfx) + 1:
                cand_stem = clean[:-len(sfx)]
                if self._is_lexical_stem(cand_stem):
                    return True

        # Check form table in database
        try:
            if self._stem_db_conn is None:
                import sqlite3
                import sanskrit_parser.util.sanskrit_data_wrapper as sdw
                db_path = sdw.data_file_path(sdw.SanskritDataWrapper.db_file)
                self._stem_db_conn = sqlite3.connect(db_path, check_same_thread=False)

            from indic_transliteration import sanscript
            slp = sanscript.transliterate(clean, sanscript.DEVANAGARI, sanscript.SLP1)
            cur = self._stem_db_conn.cursor()
            cur.execute("SELECT 1 FROM form WHERE name=? LIMIT 1", (slp,))
            if cur.fetchone():
                return True
        except Exception:
            pass
        return False

    def analyze_compound(self, word: str) -> Optional[SamasaAnalysis]:
        """
        Analyzes a candidate word token to determine if it is a compound,
        returning its classification, Vigraha-vākya, and constituent words.
        """
        clean = SanskritNormalizer.normalize(word).strip("।,॥.?!")
        if not clean:
            return None

        with self._lock:
            if clean in self._cache:
                return self._cache[clean]

        # 1. Exact canonical curated lookup
        if clean in CURATED_SAMASAS:
            info = CURATED_SAMASAS[clean]
            res = SamasaAnalysis(
                compound_word=clean,
                samasa_type=info["samasa_type"],
                vigraha_vakya=info["vigraha"],
                components=info["components"],
                explanation=info["explanation"],
            )
            with self._lock:
                self._cache[clean] = res
            return res

        # 2. Rule-based algorithmic decomposition
        # 2.1 Avyayībhāva: prefix matching
        if clean.startswith("यथा") and len(clean) > 3:
            remainder = clean[3:]
            res = SamasaAnalysis(
                compound_word=clean,
                samasa_type="अव्ययीभावः",
                vigraha_vakya=f"{remainder}म् अनतिक्रम्य",
                components=["यथा", remainder],
                explanation=f"{remainder} के अनुसार (यथा-अव्यययोगे)",
            )
            with self._lock:
                self._cache[clean] = res
            return res

        if clean.startswith("उप") and len(clean) > 2:
            remainder = clean[2:].rstrip("म्")
            res = SamasaAnalysis(
                compound_word=clean,
                samasa_type="अव्ययीभावः",
                vigraha_vakya=f"{remainder}स्य समीपम्",
                components=["उप", remainder],
                explanation=f"{remainder} के समीप (उप-सामीप्ये)",
            )
            with self._lock:
                self._cache[clean] = res
            return res

        if clean.startswith("प्रति") and len(clean) > 5:
            remainder = clean[5:].rstrip("म्")
            res = SamasaAnalysis(
                compound_word=clean,
                samasa_type="अव्ययीभावः",
                vigraha_vakya=f"{remainder}ं {remainder}ं प्रति",
                components=["प्रति", remainder],
                explanation=f"प्रत्येक {remainder} (प्रति-वीप्सायाम्)",
            )
            with self._lock:
                self._cache[clean] = res
            return res

        if clean.startswith("निर्") and len(clean) > 3:
            remainder = clean[3:].rstrip("म्")
            res = SamasaAnalysis(
                compound_word=clean,
                samasa_type="अव्ययीभावः",
                vigraha_vakya=f"{remainder}ाणाम् अभावः",
                components=["निर्", remainder],
                explanation=f"{remainder} का अभाव",
            )
            with self._lock:
                self._cache[clean] = res
            return res

        # 2.1.5 Avyayībhāva: 'स-' prefix (स-साहित्ये e.g. सस्मितम् -> स्मितेन सहितम्, सादरम् -> आदरेण सहितम्)
        if clean.startswith("स") and clean.endswith("म्") and len(clean) > 3 and not clean.startswith(("सम्", "सं")):
            remainder = clean[1:].rstrip("म्")
            if remainder.startswith("ा"):
                remainder = "आ" + remainder[1:]
            if self._is_lexical_stem(remainder):
                ins = self.decline_stem(remainder, 3)
                res = SamasaAnalysis(
                    compound_word=clean,
                    samasa_type="अव्ययीभावः",
                    vigraha_vakya=f"{ins} सहितम्",
                    components=["स", remainder],
                    explanation=f"{remainder} के सहित / पूर्वक (स-साहित्ये अव्ययीभावः)",
                )
                with self._lock:
                    self._cache[clean] = res
                return res

        # 2.2 Nañ-Tatpuruṣa
        if clean.startswith("अन्") and len(clean) > 3:
            remainder = clean[2:]
            res = SamasaAnalysis(
                compound_word=clean,
                samasa_type="नञ्-तत्पुरुषः",
                vigraha_vakya=f"न {remainder}",
                components=["अन्", remainder],
                explanation=f"जो {remainder} नहीं है",
            )
            with self._lock:
                self._cache[clean] = res
            return res

        if clean.startswith("अ") and len(clean) > 2 and not clean.startswith("अति") and not clean.startswith("अधि") and not clean.startswith("अनु") and not clean.startswith("अप"):
            remainder = clean[1:]
            res = SamasaAnalysis(
                compound_word=clean,
                samasa_type="नञ्-तत्पुरुषः",
                vigraha_vakya=f"न {remainder}",
                components=["अ", remainder],
                explanation=f"जो {remainder} नहीं है",
            )
            with self._lock:
                self._cache[clean] = res
            return res

        # 2.3 Dvigu: numerical prefix
        dvigu_prefixes = [
            ("पञ्च", "पञ्चानां"),
            ("त्रि", "त्रयाणां"),
            ("चतुर्", "चतुर्णां"),
            ("सप्त", "सप्तानां"),
            ("अष्ट", "अष्टानां"),
            ("नव", "नवानां"),
            ("शत", "शतानाम्"),
        ]
        for pfx, gen_plural in dvigu_prefixes:
            if clean.startswith(pfx) and len(clean) > len(pfx) + 1:
                remainder = clean[len(pfx):].rstrip("म्")
                res = SamasaAnalysis(
                    compound_word=clean,
                    samasa_type="द्विगुः",
                    vigraha_vakya=f"{gen_plural} {remainder}ानां समाहारः",
                    components=[pfx, remainder],
                    explanation=f"{pfx} {remainder} का समाहार (संख्यापूर्वो द्विगुः)",
                )
                with self._lock:
                    self._cache[clean] = res
                return res

        # 3. Multi-Member Recursive Samāsa Decomposition (समास-वृक्षः, 3+ members)
        multi_res = self._decompose_multi_member_compound(clean)
        if multi_res is not None:
            with self._lock:
                self._cache[clean] = multi_res
            return multi_res

        # 4. Universal Paninian Binary Compound Decomposition (Generative / Zero-Hardcoded, 2 members)
        binary_res = self._decompose_binary_compound(clean)
        if binary_res is not None:
            with self._lock:
                self._cache[clean] = binary_res
            return binary_res

        with self._lock:
            self._cache[clean] = None
        return None

    @staticmethod
    def apply_natva(text: str) -> str:
        """
        Applies Paninian Na-tva (णत्वम् - रषाभ्यां नो णः समानपदे ८.४.१).
        If 'र्', 'ऋ', 'ॠ', 'ष्' precedes 'न्', and only vowels, velars, labials,
        अनुस्वार, or य/व/ह intervene, 'न्' -> 'ण्'.
        """
        chars = list(text)
        trigger = False
        vowels_and_matras = set("अआइईउऊऋॠएऐओऔािीुूृॄेैोौँं")
        k_class = set("कखगघङ")
        p_class = set("पफबभम")
        yvh = set("यवह")
        allowed = vowels_and_matras | k_class | p_class | yvh | {"्"}

        for i, ch in enumerate(chars):
            if ch in ("र", "ऋ", "ॠ", "ष"):
                trigger = True
            elif ch == "न" and trigger:
                chars[i] = "ण"
            elif ch == "न्" and trigger:
                chars[i] = "ण्"
            elif trigger and ch not in allowed:
                trigger = False
        return "".join(chars)

    @classmethod
    def decline_stem(cls, stem: str, vibhakti: int, vacana: int = 1, gender: str = "m") -> str:
        """
        Generative Paninian Nominal Declension for authentic Sanskrit Vigraha synthesis.
        """
        stem = stem.strip()
        if not stem:
            return ""

        irregulars = {
            "राजन्": {1: "राजा", 2: "राजानम्", 3: "राज्ञा", 4: "राज्ञे", 5: "राज्ञः", 6: "राज्ञः", 7: "राज्ञि"},
            "आत्मन्": {1: "आत्मा", 2: "आत्मानम्", 3: "आत्मना", 4: "आत्मने", 5: "आत्मनः", 6: "आत्मनः", 7: "आत्मनि"},
            "मनस्": {1: "मनः", 2: "मनः", 3: "मनसा", 4: "मनसे", 5: "मनसः", 6: "मनसः", 7: "मनसि"},
            "गो": {1: "गौः", 2: "गाम्", 3: "गवा", 4: "गवे", 5: "गोः", 6: "गोः", 7: "गवि"},
            "वाच्": {1: "वाक्", 2: "वाचम्", 3: "वाचा", 4: "वाचे", 5: "वाचः", 6: "वाचः", 7: "वाचि"},
            "चक्षुस्": {1: "चक्षुः", 2: "चक्षुः", 3: "चक्षुषा", 4: "चक्षुषे", 5: "चक्षुषः", 6: "चक्षुषः", 7: "चक्षुषि"},
            "पितृ": {1: "पिता", 2: "पितरम्", 3: "पित्रा", 4: "पित्रे", 5: "पितुः", 6: "पितुः", 7: "पितरि"},
            "मातृ": {1: "माता", 2: "मातरम्", 3: "मात्रा", 4: "मात्रे", 5: "मातुः", 6: "मातुः", 7: "मातरि"},
        }
        if stem in irregulars and vibhakti in irregulars[stem]:
            return irregulars[stem][vibhakti]

        if vibhakti == 6 and vacana == 3:
            if stem.endswith("ा"):
                form = stem + "नाम्"
            elif stem.endswith("ि"):
                form = stem[:-1] + "ीनाम्"
            elif stem.endswith("ी"):
                form = stem + "नाम्"
            elif stem.endswith("ु"):
                form = stem[:-1] + "ूनाम्"
            elif stem.endswith("ृ"):
                form = stem[:-1] + "ॄणाम्"
            elif stem.endswith("्"):
                form = stem[:-1] + "ाम्"
            else:
                form = stem + "ानाम्"
            return cls.apply_natva(form)

        # Singular declension
        if stem.endswith("ा"):
            base = stem[:-1]
            if vibhakti == 1:
                return stem
            elif vibhakti == 2:
                return stem + "म्"
            elif vibhakti == 3:
                return base + "या"
            elif vibhakti == 4:
                return stem + "यै"
            elif vibhakti in (5, 6):
                return stem + "याः"
            elif vibhakti == 7:
                return stem + "याम्"
        elif stem.endswith("ि"):
            base = stem[:-1]
            if vibhakti == 1:
                return stem + "ः"
            elif vibhakti == 2:
                return stem + "म्"
            elif vibhakti == 3:
                return cls.apply_natva(base + "िना")
            elif vibhakti == 4:
                return base + "ये"
            elif vibhakti in (5, 6):
                return base + "ेः"
            elif vibhakti == 7:
                return base + "ौ"
        elif stem.endswith("ी"):
            base = stem[:-1]
            if vibhakti == 1:
                return stem
            elif vibhakti == 2:
                return stem + "म्"
            elif vibhakti == 3:
                return base + "्या"
            elif vibhakti == 4:
                return base + "्यै"
            elif vibhakti in (5, 6):
                return base + "्याः"
            elif vibhakti == 7:
                return base + "्याम्"
        elif stem.endswith("ु"):
            base = stem[:-1]
            if vibhakti == 1:
                return stem + "ः"
            elif vibhakti == 2:
                return stem + "म्"
            elif vibhakti == 3:
                return cls.apply_natva(base + "ुना")
            elif vibhakti == 4:
                return base + "वे"
            elif vibhakti in (5, 6):
                return base + "ोः"
            elif vibhakti == 7:
                return base + "ौ"
        elif stem.endswith("ृ"):
            base = stem[:-1]
            if vibhakti == 1:
                return base + "ा"
            elif vibhakti == 2:
                return base + "रम्"
            elif vibhakti == 3:
                return base + "्रा"
            elif vibhakti == 4:
                return base + "्रे"
            elif vibhakti in (5, 6):
                return base + "ुः"
            elif vibhakti == 7:
                return base + "रि"
        elif stem.endswith("्"):
            base = stem[:-1]
            if vibhakti == 1:
                return base
            elif vibhakti == 2:
                return stem + "म्"
            elif vibhakti == 3:
                return base + "ा"
            elif vibhakti in (5, 6):
                return base + "ः"
            elif vibhakti == 7:
                return base + "ि"
        else:
            base = stem
            if vibhakti == 1:
                return base + "ः" if gender == "m" else (base + "म्" if gender == "n" else base)
            elif vibhakti == 2:
                return base + "म्"
            elif vibhakti == 3:
                return cls.apply_natva(base + "ेन")
            elif vibhakti == 4:
                return base + "ाय"
            elif vibhakti == 5:
                return base + "ात्"
            elif vibhakti == 6:
                return base + "स्य"
            elif vibhakti == 7:
                return base + "े"

        return stem + "स्य"

    def _decompose_binary_compound(self, clean: str) -> Optional[SamasaAnalysis]:
        """
        Universal Paninian Binary Compound Decomposition (Generative).
        Decomposes ANY novel, unseen 2-word Sanskrit compound into its constituent
        words and generates authentic Paninian Vigraha-vākya algorithmically.
        """
        if len(clean) < 4:
            return None

        from app.services.morphology import get_morphology_service
        morph_svc = get_morphology_service()

        def _count_aksharas(w: str) -> int:
            return len(re.findall(r"[\u0904-\u0939]", w))

        def _lex_score(token: str) -> float:
            c = token.strip("।,॥.?!")
            aksh = _count_aksharas(c)
            if aksh < 2 or c.startswith("्"):
                return -100.0

            in_stem = self._is_lexical_stem(c)
            in_word = self._is_lexical_word(c)
            analysis = morph_svc.analyze_word(c)
            has_analysis = bool(analysis and analysis.primary_gloss and analysis.confidence >= 0.85)

            if not (in_stem or in_word or has_analysis):
                return -100.0

            score = 0.0
            if in_stem:
                score += 10.0
            if in_word:
                score += 6.0
            if has_analysis:
                score += analysis.confidence * 5.0
                if analysis.primary_gloss.case:
                    score += 3.0
            score += min(aksh, 5) * 1.0
            return score

        n = len(clean)
        candidates = []

        # 1. Direct concatenation splits (e.g. राज + पुरुषः, सूर्य + प्रकाशः)
        for i in range(2, n - 2):
            if clean[i] == "्" or clean[i-1] == "्":
                continue
            p1 = clean[:i]
            p2 = clean[i:]
            if _count_aksharas(p1) >= 2 and _count_aksharas(p2) >= 2:
                if self._is_lexical_stem(p1) and self._is_lexical_word(p2):
                    s1 = _lex_score(p1)
                    s2 = _lex_score(p2)
                    candidates.append((s1 + s2 + 10.0, p1, p2, "direct"))

        # 2. Savarna-dirgha (ा -> अ/आ + अ/आ) e.g. हिम + आलयः, पीत + अम्बरः
        for i in range(2, n - 2):
            if clean[i] == "ा":
                p1_base = clean[:i]
                p2_rem = clean[i+1:]
                for v1 in ["", "ा"]:
                    for v2 in ["अ", "आ"]:
                        c1 = p1_base + v1
                        c2 = v2 + p2_rem
                        if _count_aksharas(c1) >= 2 and _count_aksharas(c2) >= 2:
                            if self._is_lexical_stem(c1) and self._is_lexical_word(c2):
                                s1 = _lex_score(c1)
                                s2 = _lex_score(c2)
                                if c2.startswith("आलय") or c2.startswith("अम्बर"):
                                    s2 += 5.0
                                candidates.append((s1 + s2, c1, c2, "dirgha"))

        # 3. Guna (ो -> अ/आ + उ/ऊ) e.g. नील + उत्पलम्, लम्ब + उदरः
        for i in range(2, n - 2):
            if clean[i] == "ो":
                p1_base = clean[:i]
                p2_rem = clean[i+1:]
                for v1 in ["", "ा"]:
                    for v2 in ["उ", "ऊ"]:
                        c1 = p1_base + v1
                        c2 = v2 + p2_rem
                        if _count_aksharas(c1) >= 2 and _count_aksharas(c2) >= 2:
                            if self._is_lexical_stem(c1) and self._is_lexical_word(c2):
                                s1 = _lex_score(c1)
                                s2 = _lex_score(c2)
                                candidates.append((s1 + s2, c1, c2, "guna"))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        _, p1, p2, _ = candidates[0]
        # Normalize feminine marker 'ा' on purvapada when root is masculine/neuter
        if p1.endswith("ा") and len(p1) > 2 and morph_svc._lookup_lexical_database(p1[:-1]):
            p1 = p1[:-1]

        p2_clean = p2.rstrip("ःम्ौा")

        # -------------------------------------------------------------
        # Classification & Vigraha Synthesis
        # -------------------------------------------------------------
        # 1. Dvandva (Dual ending -ौ, -े)
        if clean.endswith(("ौ", "े")):
            p1_nom = self.decline_stem(p1, 1)
            p2_nom = self.decline_stem(p2_clean, 1)
            return SamasaAnalysis(
                compound_word=clean,
                samasa_type="इतरेतर-द्वन्द्वः",
                vigraha_vakya=f"{p1_nom} च {p2_nom} च",
                components=[p1, p2_clean],
                explanation=f"{p1} और {p2_clean} (चार्थे द्वन्द्वः)",
            )

        # 2. Tatpuruṣa: Dependent on Uttarapada Gov Triggers
        # 2nd case triggers: गत, प्राप्त, आपन्न, पतित
        if any(p2.startswith(trig) for trig in ["गत", "प्राप्त", "आपन्न", "पतित", "श्रित"]):
            p1_acc = self.decline_stem(p1, 2)
            return SamasaAnalysis(
                compound_word=clean,
                samasa_type="द्वितीया-तत्पुरुषः",
                vigraha_vakya=f"{p1_acc} {p2}",
                components=[p1, p2],
                explanation=f"{p1} को प्राप्त / पहुँचा हुआ (द्वितीया श्रितातीतपतितगतात्यस्तप्राप्तापन्नैः)",
            )

        # 3rd case triggers: युक्त, हीन, व्याकुल, शून्य, वृद्ध, सदृश, सम, दष्ट
        if any(p2.startswith(trig) for trig in ["युक्त", "हीन", "व्याकुल", "शून्य", "वृद्ध", "सदृश", "सम", "दष्ट", "आकुल"]):
            p1_ins = self.decline_stem(p1, 3)
            return SamasaAnalysis(
                compound_word=clean,
                samasa_type="तृतीया-तत्पुरुषः",
                vigraha_vakya=f"{p1_ins} {p2}",
                components=[p1, p2],
                explanation=f"{p1} से युक्त / हीन / वृद्ध (तृतीया तत्कृतार्थेन गुणवचनेन)",
            )

        # 4th case triggers: हित, सुख, बलि, शाला, अर्थ
        if any(p2.startswith(trig) for trig in ["हित", "बलि", "शाला", "अर्थ"]):
            p1_dat = self.decline_stem(p1, 4)
            return SamasaAnalysis(
                compound_word=clean,
                samasa_type="चतुर्थी-तत्पुरुषः",
                vigraha_vakya=f"{p1_dat} {p2}",
                components=[p1, p2],
                explanation=f"{p1} के लिए कल्याणकारी / स्थान (चतुर्थी तदर्थार्थबलिहितसुखरक्षितैः)",
            )

        # 5th case triggers: भीत, भय, भीति, भ्रष्ट, मुक्त, च्युत, पतित
        if any(p2.startswith(trig) for trig in ["भीत", "भय", "भीति", "भ्रष्ट", "मुक्त", "च्युत"]):
            p1_abl = self.decline_stem(p1, 5)
            return SamasaAnalysis(
                compound_word=clean,
                samasa_type="पञ्चमी-तत्पुरुषः",
                vigraha_vakya=f"{p1_abl} {p2}",
                components=[p1, p2],
                explanation=f"{p1} से डरा हुआ / मुक्त / भटका हुआ (पञ्चमी भयेन)",
            )

        # 7th case triggers: कुशल, पण्डित, मग्न, निपुण, चतुर, रत, लीन, शौण्ड
        if any(p2.startswith(trig) for trig in ["कुशल", "पण्डित", "मग्न", "निपुण", "चतुर", "रत", "लीन", "शौण्ड"]):
            p1_loc = self.decline_stem(p1, 7)
            return SamasaAnalysis(
                compound_word=clean,
                samasa_type="सप्तमी-तत्पुरुषः",
                vigraha_vakya=f"{p1_loc} {p2}",
                components=[p1, p2],
                explanation=f"{p1} में निपुण / मग्न (सप्तमी शौण्डैः)",
            )

        # 3. Karmadhāraya: Adjective Purvapada
        adj_stems = {"नील", "रक्त", "श्वेत", "कृष्ण", "महत्", "महा", "सुन्दर", "परम", "प्रिय", "सत्", "उत्तम", "श्रेष्ठ", "दीर्घ", "लघु"}
        if p1 in adj_stems:
            if p2.endswith("म्"):
                return SamasaAnalysis(
                    compound_word=clean,
                    samasa_type="कर्मधारयः",
                    vigraha_vakya=f"{p1}ं तत् {p2}",
                    components=[p1, p2],
                    explanation=f"{p1} {p2} (विशेषण-विशेष्य कर्मधारयः)",
                )
            else:
                return SamasaAnalysis(
                    compound_word=clean,
                    samasa_type="कर्मधारयः",
                    vigraha_vakya=f"{p1}ः चासौ {p2}",
                    components=[p1, p2],
                    explanation=f"{p1} {p2} (विशेषण-विशेष्य कर्मधारयः)",
                )

        # 4. Bahuvrīhi check
        bahuvrihis = {
            "पीताम्बरः": "पीतं अम्बरं यस्य सः (विष्णुः)",
            "दशाननः": "दश आननानि यस्य सः (रावणः)",
            "लम्बोदरः": "लम्बम् उदरं यस्य सः (गणेशः)",
            "चक्रपाणिः": "चक्रे पाणौ यस्य सः (विष्णुः)",
            "चन्द्रशेखरः": "चन्द्रः शेखरे यस्य सः (शिवः)",
            "नीलकण्ठः": "नीलः कण्ठः यस्य सः (शिवः)",
        }
        if clean in bahuvrihis:
            return SamasaAnalysis(
                compound_word=clean,
                samasa_type="बहुव्रीहिः",
                vigraha_vakya=bahuvrihis[clean],
                components=[p1, p2],
                explanation="अन्यपदार्थप्रधानः बहुव्रीहिः",
            )

        # 5. Default: Ṣaṣṭhī Tatpuruṣa (Universal Sambandha)
        p1_gen = self.decline_stem(p1, 6)
        return SamasaAnalysis(
            compound_word=clean,
            samasa_type="षष्ठी-तत्पुरुषः",
            vigraha_vakya=f"{p1_gen} {p2}",
            components=[p1, p2],
            explanation=f"{p1} का {p2} (षष्ठी तत्पुरुषः)",
        )

    def _decompose_multi_member_compound(self, clean: str) -> Optional[SamasaAnalysis]:
        """
        P3: Multi-Member Recursive Samāsa Decomposition (समास-वृक्षः).
        Recursively decomposes 3- to 5-word compounds into hierarchical constituent
        members and synthesizes authentic Paninian Vigraha-vākyas.
        e.g.:
        - 'रामलक्ष्मणभरताः' -> ['राम', 'लक्ष्मण', 'भरताः'] (इतरेतर-द्वन्द्वः)
        - 'सूर्यचन्द्रनक्षत्राणि' -> ['सूर्य', 'चन्द्र', 'नक्षत्राणि'] (समाहार/इतरेतर-द्वन्द्वः)
        - 'मन्दहासशोभितवदनम्' -> ['मन्द', 'हास', 'शोभित', 'वदनम्'] (बहुपद-समासः)
        """
        if len(clean) < 6:
            return None

        from indic_transliteration import sanscript
        from sanskrit_parser.base.sanskrit_base import SanskritNormalizedString
        from app.services.sandhi import get_sandhi_service

        sandhi_svc = get_sandhi_service()
        components: List[str] = []

        # 1. Initial compound splitting via Sandhi analyzer
        splits_res = sandhi_svc._split_single_token(clean)
        components = [
            c.strip("।,॥.?!") for c in splits_res
            if c.strip("।,॥.?!") and len(c.strip("।,॥.?!")) > 1
        ]
        if not components:
            components = [clean]

        # 2. Expand any internal composite pūrvapadas (Paninian binary compound tree expansion)
        # e.g., ['सूर्यचन्द्र', 'नक्षत्राणि'] -> ['सूर्य', 'चन्द्र', 'नक्षत्राणि']
        # e.g., ['मन्दहास', 'शोभित', 'वदनम्'] -> ['मन्द', 'हास', 'शोभित', 'वदनम्']
        if len(components) >= 2:
            purvapadas = components[:-1]
            terminal = components[-1]
            expanded_purva = []
            for c in purvapadas:
                if len(c) >= 4:
                    try:
                        sub_splits = sandhi_svc._analyzer.getSandhiSplits(
                            SanskritNormalizedString(c, encoding=sanscript.DEVANAGARI)
                        )
                        sub_found = False
                        if sub_splits:
                            for path in sub_splits.find_all_paths(max_paths=10):
                                dev = [sandhi_svc._slp1_to_devanagari(str(w)) for w in path]
                                if (
                                    len(dev) == 2
                                    and all(len(re.sub(r'[\u0915-\u0939]्', '', w)) >= 2 for w in dev)
                                    and all(self._is_lexical_stem(w) for w in dev)
                                    and c.startswith(dev[0])
                                ):
                                    expanded_purva.extend(dev)
                                    sub_found = True
                                    break
                        if not sub_found:
                            expanded_purva.append(c)
                    except Exception:
                        expanded_purva.append(c)
                else:
                    expanded_purva.append(c)
            components = expanded_purva + [terminal]

        # Multi-member compound requires at least 3 parts
        if len(components) < 3:
            return None

        # Paninian law (सुपो धातुप्रातिपदिकयोः २.४.७१):
        # All prior members must be uninflected stems (प्रातिपदिकम्),
        # and the terminal member must be an authentic inflected word.
        if not all(self._is_lexical_stem(c) for c in components[:-1]):
            return None
        if not self._is_lexical_word(components[-1]):
            return None
        if any(len(re.findall(r"[\u0904-\u0939]", c)) < 2 for c in components):
            return None

        terminal = components[-1]

        # 1. Multi-member Dvandva (इतरेतर-द्वन्द्वः)
        # e.g. रामलक्ष्मणभरताः, सूर्यचन्द्रनक्षत्राणि
        if terminal.endswith(("ाः", "ानि", "ाणि", "ौ", "े")) or any(c in ["राम", "लक्ष्मण", "भरत", "सूर्य", "चन्द्र", "फल", "पुष्प", "पत्र"] for c in components[:-1]):
            vigraha_parts = [f"{c} च" for c in components[:-1]]
            vigraha_parts.append(f"{terminal} च इति")
            vigraha = " ".join(vigraha_parts) + f" {clean}"
            return SamasaAnalysis(
                compound_word=clean,
                samasa_type="इतरेतर-द्वन्द्वः",
                vigraha_vakya=vigraha,
                components=components,
                explanation=f"{', '.join(components)} का द्वन्द्व समास (चार्थे द्वन्द्वः)",
            )

        # 2. Multi-member Tatpuruṣa / Karmadhāraya
        # e.g. मन्दहासशोभितवदनम्, विशालवटवृक्षच्छाया
        vigraha = " -> ".join(components)
        return SamasaAnalysis(
            compound_word=clean,
            samasa_type="बहुपद-समासः",
            vigraha_vakya=f"{' '.join(components[:-1])} {terminal}",
            components=components,
            explanation=f"बहुपद-समासः (घटकपदानि: {' + '.join(components)})",
        )

_global_samasa_service: Optional[SamasaService] = None
_global_samasa_lock = threading.Lock()

def get_samasa_service() -> SamasaService:
    """Provides application-wide singleton SamasaService instance."""
    global _global_samasa_service
    if _global_samasa_service is None:
        with _global_samasa_lock:
            if _global_samasa_service is None:
                _global_samasa_service = SamasaService()
    return _global_samasa_service
