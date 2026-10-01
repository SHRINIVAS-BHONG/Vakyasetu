from collections import OrderedDict
from dataclasses import dataclass, field
from functools import lru_cache
import logging
import threading
from typing import List, Tuple, Optional

from indic_transliteration import sanscript
from sanskrit_parser.base.sanskrit_base import SanskritNormalizedString

from app.core.normalizer import SanskritNormalizer
from app.models.schemas import SandhiSplitOption, SandhiRuleExplanation

logger = logging.getLogger(__name__)

@dataclass
class SandhiSplitResult:
    split_words: List[str]
    confidence: float
    all_candidates: List[SandhiSplitOption]
    rules: List[SandhiRuleExplanation] = field(default_factory=list)

class SandhiService:
    """
    Mayank's Production Sandhi Splitting Engine for VākyaSetu.
    Features:
    - Shared LexicalSandhiAnalyzer singleton (eliminates duplicate lexicon memory).
    - LRU-cached phonological transliterations.
    - Thread-safe bounded LRU split cache for instant repeated sentence resolution.
    - Zero-width character sanitization via SanskritNormalizer.
    """

    _shared_split_cache: OrderedDict[Tuple[str, int], SandhiSplitResult] = OrderedDict()
    _split_cache_lock: threading.Lock = threading.Lock()
    _max_cache_size: int = 2048

    def __init__(self):
        from app.services.morphology import MorphologyService
        self._analyzer = MorphologyService._get_analyzer()

    @staticmethod
    @lru_cache(maxsize=4096)
    def _devanagari_to_slp1(devanagari_text: str) -> str:
        return sanscript.transliterate(devanagari_text, sanscript.DEVANAGARI, sanscript.SLP1)

    @staticmethod
    @lru_cache(maxsize=4096)
    def _slp1_to_devanagari(slp1_text: str) -> str:
        dev = sanscript.transliterate(slp1_text, sanscript.SLP1, sanscript.DEVANAGARI)
        # Padānta sakāra normalization for school display:
        # e.g., 'बालकस्' at word boundary is conventionally presented as 'बालकः'
        if dev.endswith("स्"):
            dev = dev[:-2] + "ः"
        return dev

    def _is_valid_lexical_token(self, token: str) -> bool:
        """Checks if a word is already an intact valid inflected form, avyaya, or upasarga verb."""
        from app.services.morphology import NCERT_AVYAYAS, get_morphology_service
        clean = token.strip("।,॥.?!")
        if not clean:
            return True
        if clean in NCERT_AVYAYAS:
            return True
        morph_svc = get_morphology_service()
        if morph_svc._lookup_lexical_database(clean):
            return True
        # Check if word is already a valid inflected form via Paninian declension rules
        analysis = morph_svc.analyze_word(clean)
        if analysis and analysis.primary_gloss and analysis.confidence >= 0.85:
            return True
        return False

    def _split_single_token(self, token_text: str, max_paths: int = 5) -> List[str]:
        """Splits an individual fused token using the sandhi graph."""
        clean = token_text.strip("।,॥.?!")
        if not clean:
            return []
        try:
            slp1_input = self._devanagari_to_slp1(clean)
            graph = self._analyzer.getSandhiSplits(SanskritNormalizedString(slp1_input))
            if graph:
                paths = graph.find_all_paths(max_paths=max_paths)
                for path in paths:
                    dev_words = [self._slp1_to_devanagari(str(w)) for w in path]
                    if dev_words:
                        return dev_words
        except Exception as e:
            logger.debug(f"Sandhi split failed on '{token_text}': {e}")
        return [clean]

    @classmethod
    def explain_sandhi_rule(cls, w1: str, w2: str) -> Optional[SandhiRuleExplanation]:
        """
        P3: Paninian Sandhi Sūtra Attribution.
        Identifies the classical Paninian grammar rule governing the phonetic junction between w1 and w2.
        """
        c1_dev = w1.strip("।,॥.?!")
        c2_dev = w2.strip("।,॥.?!")
        if not c1_dev or not c2_dev:
            return None

        s1 = cls._devanagari_to_slp1(c1_dev)
        s2 = cls._devanagari_to_slp1(c2_dev)
        if not s1 or not s2:
            return None

        p1 = s1[-1]
        p2 = s2[0]

        vowels = {'a', 'A', 'i', 'I', 'u', 'U', 'f', 'F', 'x', 'e', 'E', 'o', 'O'}
        voiced_consonants = {
            'g', 'G', 'N', 'j', 'J', 'Y', 'q', 'Q', 'R', 'd', 'D', 'n',
            'b', 'B', 'm', 'y', 'r', 'l', 'v', 'h'
        }

        junction = f"{c1_dev} + {c2_dev}"

        # 1. स्वरसन्धिः (Vowel Sandhi)
        # 1.1 Dīrgha (अकः सवर्णे दीर्घः ६.१.१०१)
        if (p1 in {'a', 'A'} and p2 in {'a', 'A'}) or \
           (p1 in {'i', 'I'} and p2 in {'i', 'I'}) or \
           (p1 in {'u', 'U'} and p2 in {'u', 'U'}) or \
           (p1 in {'f', 'F'} and p2 in {'f', 'F'}):
            return SandhiRuleExplanation(
                junction=junction,
                rule_name="दीर्घसन्धिः",
                sutra="अकः सवर्णे दीर्घः (६.१.१०१)",
                sandhi_type="स्वरसन्धिः",
                explanation=f"ह्रस्व वा दीर्घ स्वर के बाद सवर्ण स्वर आने पर दोनों मिलकर दीर्घ हो जाते हैं ({p1} + {p2} → दीर्घ स्वर)।",
            )

        # 1.2 Guṇa (आद्गुणः ६.१.८७)
        if p1 in {'a', 'A'} and p2 in {'i', 'I', 'u', 'U', 'f', 'F', 'x'}:
            target = "ए" if p2 in {'i', 'I'} else ("ओ" if p2 in {'u', 'U'} else "अर्")
            return SandhiRuleExplanation(
                junction=junction,
                rule_name="गुणसन्धिः",
                sutra="आद्गुणः (६.१.८७)",
                sandhi_type="स्वरसन्धिः",
                explanation=f"अ/आ के बाद इ/उ/ऋ आने पर दोनों के स्थान पर गुण एकादेश ({target}) हो जाता है।",
            )

        # 1.3 Vṛddhi (वृद्धिरेचि ६.१.८८)
        if p1 in {'a', 'A'} and p2 in {'e', 'E', 'o', 'O'}:
            target = "ऐ" if p2 in {'e', 'E'} else "औ"
            return SandhiRuleExplanation(
                junction=junction,
                rule_name="वृद्धिसन्धिः",
                sutra="वृद्धिरेचि (६.१.८८)",
                sandhi_type="स्वरसन्धिः",
                explanation=f"अ/आ के बाद एच् (ए, ऐ, ओ, औ) आने पर दोनों के स्थान पर वृद्धि एकादेश ({target}) हो जाता है।",
            )

        # 1.4 Yaṇ (इको यणचि ६.१.७७)
        if p1 in {'i', 'I', 'u', 'U', 'f', 'F'} and p2 in vowels and p2 not in {p1, p1.upper(), p1.lower()}:
            target = "य्" if p1 in {'i', 'I'} else ("व्" if p1 in {'u', 'U'} else "र्")
            return SandhiRuleExplanation(
                junction=junction,
                rule_name="यण्सन्धिः",
                sutra="इको यणचि (६.१.७७)",
                sandhi_type="स्वरसन्धिः",
                explanation=f"इक् (इ, उ, ऋ) के स्थान पर असमान स्वर परे होने पर यण् ({target}) आदेश होता है।",
            )

        # 1.5 Ayādi (एचोऽयवायावः ६.१.७८)
        if p1 in {'e', 'E', 'o', 'O'} and p2 in vowels:
            target = "अय" if p1 == 'e' else ("आय" if p1 == 'E' else ("अव" if p1 == 'o' else "आव"))
            return SandhiRuleExplanation(
                junction=junction,
                rule_name="अयादिसन्धिः",
                sutra="एचोऽयवायावः (६.१.७८)",
                sandhi_type="स्वरसन्धिः",
                explanation=f"एच् (ए, ऐ, ओ, औ) के बाद कोई भी स्वर आने पर क्रमशः अय्, आय्, अव्, आव् आदेश होता है।",
            )

        # 1.6 Pūrvarūpa (एङः पदान्तादति ६.१.१०९)
        if p1 in {'e', 'o'} and p2 == 'a':
            return SandhiRuleExplanation(
                junction=junction,
                rule_name="पूर्वरूपसन्धिः",
                sutra="एङः पदान्तादति (६.१.१०९)",
                sandhi_type="स्वरसन्धिः",
                explanation="पदान्त ए अथवा ओ के बाद ह्रस्व 'अ' आने पर 'अ' का पूर्वरूप होकर अवग्रह (ऽ) बन जाता है।",
            )

        # 2. विसर्गसन्धिः (Visarga Sandhi)
        if p1 in {'H', 's', 'r'} or c1_dev.endswith("ः") or c1_dev.endswith("स्"):
            # 2.1 Utva
            if (s1.endswith("aH") or s1.endswith("as")) and (p2 == 'a' or p2 in voiced_consonants):
                return SandhiRuleExplanation(
                    junction=junction,
                    rule_name="विसर्गसन्धिः (उत्वम्)",
                    sutra="अतो रोरप्लुतादप्लुते (६.१.११३) / हशि च (६.१.११४)",
                    sandhi_type="विसर्गसन्धिः",
                    explanation="अकारोत्तर विसर्ग के बाद 'अ' अथवा हश् (घोष वर्ण) आने पर विसर्ग को 'उ' होकर 'ओ' बन जाता है।",
                )
            # 2.2 Satva
            if p2 in {'c', 'C', 'w', 'W', 't', 'T', 'S', 'z', 's'}:
                return SandhiRuleExplanation(
                    junction=junction,
                    rule_name="विसर्गसन्धिः (सत्वम्)",
                    sutra="विसर्जनीयस्य सः (८.३.३४)",
                    sandhi_type="विसर्गसन्धिः",
                    explanation="विसर्ग के बाद खर् वर्ण (च, छ, ट, ठ, त, थ, श, ष, स) आने पर विसर्ग का सत्व (श्, ष्, स्) हो जाता है।",
                )
            # 2.3 Rutva
            if not s1.endswith("aH") and not s1.endswith("AH") and (p2 in vowels or p2 in voiced_consonants):
                return SandhiRuleExplanation(
                    junction=junction,
                    rule_name="विसर्गसन्धिः (रुत्वम्)",
                    sutra="ससजुषो रुः (८.२.६६)",
                    sandhi_type="विसर्गसन्धिः",
                    explanation="अ/आ से भिन्न स्वर के बाद विसर्ग हो और आगे स्वर या घोष व्यंजन हो, तो विसर्ग का 'र्' हो जाता है।",
                )
            # 2.4 Lopa
            return SandhiRuleExplanation(
                junction=junction,
                rule_name="विसर्गसन्धिः (लोपः)",
                sutra="भोभगोअघोअपूर्वस्य योऽशि (८.३.१७) / लोपः",
                sandhi_type="विसर्गसन्धिः",
                explanation="विशिष्ट स्थितियों में स्वर या व्यंजन परे होने पर विसर्ग का लोप हो जाता है।",
            )

        # 3. व्यञ्जनसन्धिः (Consonant Sandhi)
        # 3.1 Ścutva
        if p1 in {'s', 't', 'T', 'd', 'D', 'n'} and p2 in {'S', 'c', 'C', 'j', 'J', 'Y'}:
            return SandhiRuleExplanation(
                junction=junction,
                rule_name="श्चुत्वसन्धिः",
                sutra="स्तोः श्चुना श्चुः (८.४.४०)",
                sandhi_type="व्यञ्जनसन्धिः",
                explanation="सकार तथा त-वर्ग का शकार तथा च-वर्ग के योग में शकार तथा च-वर्ग आदेश हो जाता है।",
            )
        # 3.2 Ṣṭutva
        if p1 in {'s', 't', 'T', 'd', 'D', 'n'} and p2 in {'z', 'w', 'W', 'q', 'Q', 'R'}:
            return SandhiRuleExplanation(
                junction=junction,
                rule_name="ष्टुत्वसन्धिः",
                sutra="ष्टुना ष्टुः (८.४.४१)",
                sandhi_type="व्यञ्जनसन्धिः",
                explanation="सकार तथा त-वर्ग का षकार तथा ट-वर्ग के योग में षकार तथा ट-वर्ग आदेश हो जाता है।",
            )
        # 3.3 Jaśtva
        if p1 in {'k', 'c', 'w', 't', 'p'} and (p2 in vowels or p2 in voiced_consonants):
            return SandhiRuleExplanation(
                junction=junction,
                rule_name="जश्त्वसन्धिः",
                sutra="झलां जशोऽन्ते (८.२.३९)",
                sandhi_type="व्यञ्जनसन्धिः",
                explanation="पदान्त झल् (वर्गीय प्रथम वर्ण) के बाद स्वर अथवा घोष व्यंजन आने पर वर्ण अपने ही वर्ग का तृतीय वर्ण हो जाता है।",
            )
        # 3.4 Anunāsika
        if p1 in {'k', 'c', 'w', 't', 'p'} and p2 in {'N', 'Y', 'R', 'n', 'm'}:
            return SandhiRuleExplanation(
                junction=junction,
                rule_name="अनुनासिकसन्धिः",
                sutra="यरोऽनुनासिकेऽनुनासिको वा (८.४.४५)",
                sandhi_type="व्यञ्जनसन्धिः",
                explanation="पदान्त स्पर्श वर्ण के बाद अनुनासिक वर्ण आने पर पूर्व वर्ण अपने वर्ग का पञ्चम (अनुनासिक) वर्ण हो जाता है।",
            )
        # 3.5 Anusvāra
        if p1 == 'm' and p2 not in vowels:
            return SandhiRuleExplanation(
                junction=junction,
                rule_name="अनुस्वारसन्धिः",
                sutra="मोऽनुस्वारः (८.३.२३)",
                sandhi_type="व्यञ्जनसन्धिः",
                explanation="पदान्त मकार के बाद कोई भी व्यंजन आने पर मकार का अनुस्वार (ं) हो जाता है।",
            )

        return None

    def split(self, text: str, max_paths: int = 5) -> SandhiSplitResult:
        """
        Segments a Sanskrit sentence into constituent words and identifies Paninian Sandhi rules.
        Preserves already-intact valid words and segments fused compounds/sandhis.
        """
        clean_text = SanskritNormalizer.normalize(text).strip("।,॥.?!")
        if not clean_text:
            return SandhiSplitResult(split_words=[], confidence=1.0, all_candidates=[], rules=[])

        cache_key = (clean_text, max_paths)
        with self._split_cache_lock:
            if cache_key in self._shared_split_cache:
                self._shared_split_cache.move_to_end(cache_key)
                return self._shared_split_cache[cache_key]

        tokens = clean_text.split()
        final_splits: List[str] = []
        all_options: List[SandhiSplitOption] = []
        detected_rules: List[SandhiRuleExplanation] = []

        if len(tokens) > 1:
            for t in tokens:
                if self._is_valid_lexical_token(t):
                    final_splits.append(t)
                else:
                    split_t = self._split_single_token(t, max_paths=max_paths)
                    if len(split_t) > 1:
                        for s_idx in range(len(split_t) - 1):
                            r = self.explain_sandhi_rule(split_t[s_idx], split_t[s_idx+1])
                            if r:
                                detected_rules.append(r)
                    final_splits.extend(split_t)
            all_options = [SandhiSplitOption(split_words=final_splits, confidence=0.95)]
        else:
            # Single chunk: check if intact or fused
            single = tokens[0]
            if self._is_valid_lexical_token(single):
                final_splits = [single]
                all_options = [SandhiSplitOption(split_words=[single], confidence=1.0)]
            else:
                final_splits = self._split_single_token(single, max_paths=max_paths)
                if len(final_splits) > 1:
                    for s_idx in range(len(final_splits) - 1):
                        r = self.explain_sandhi_rule(final_splits[s_idx], final_splits[s_idx+1])
                        if r:
                            detected_rules.append(r)
                all_options = [SandhiSplitOption(split_words=final_splits, confidence=0.95)]

        if not final_splits:
            final_splits = tokens
            all_options = [SandhiSplitOption(split_words=tokens, confidence=0.85)]

        result = SandhiSplitResult(
            split_words=final_splits,
            confidence=all_options[0].confidence if all_options else 0.85,
            all_candidates=all_options,
            rules=detected_rules,
        )

        with self._split_cache_lock:
            if len(self._shared_split_cache) >= self._max_cache_size:
                self._shared_split_cache.popitem(last=False)
            self._shared_split_cache[cache_key] = result

        return result

_global_sandhi_service: Optional[SandhiService] = None
_global_sandhi_lock = threading.Lock()

def get_sandhi_service() -> SandhiService:
    """Provides application-wide singleton SandhiService instance."""
    global _global_sandhi_service
    if _global_sandhi_service is None:
        with _global_sandhi_lock:
            if _global_sandhi_service is None:
                _global_sandhi_service = SandhiService()
    return _global_sandhi_service

