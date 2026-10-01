from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
import logging
import threading
from typing import List, Tuple, Optional

from indic_transliteration import sanscript
from sanskrit_parser.base.sanskrit_base import SanskritNormalizedString

from app.core.normalizer import SanskritNormalizer
from app.models.schemas import SandhiSplitOption

logger = logging.getLogger(__name__)

@dataclass
class SandhiSplitResult:
    split_words: List[str]
    confidence: float
    all_candidates: List[SandhiSplitOption]

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
        return bool(morph_svc._lookup_lexical_database(clean))

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

    def split(self, text: str, max_paths: int = 5) -> SandhiSplitResult:
        """
        Segments a Sanskrit sentence into constituent words.
        Preserves already-intact valid words and segments fused compounds/sandhis.
        """
        clean_text = SanskritNormalizer.normalize(text).strip("।,॥.?!")
        if not clean_text:
            return SandhiSplitResult(split_words=[], confidence=1.0, all_candidates=[])

        cache_key = (clean_text, max_paths)
        with self._split_cache_lock:
            if cache_key in self._shared_split_cache:
                self._shared_split_cache.move_to_end(cache_key)
                return self._shared_split_cache[cache_key]

        tokens = clean_text.split()
        final_splits: List[str] = []
        all_options: List[SandhiSplitOption] = []

        if len(tokens) > 1:
            for t in tokens:
                if self._is_valid_lexical_token(t):
                    final_splits.append(t)
                else:
                    split_t = self._split_single_token(t, max_paths=max_paths)
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
                all_options = [SandhiSplitOption(split_words=final_splits, confidence=0.95)]

        if not final_splits:
            final_splits = tokens
            all_options = [SandhiSplitOption(split_words=tokens, confidence=0.85)]

        result = SandhiSplitResult(
            split_words=final_splits,
            confidence=all_options[0].confidence if all_options else 0.85,
            all_candidates=all_options
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

