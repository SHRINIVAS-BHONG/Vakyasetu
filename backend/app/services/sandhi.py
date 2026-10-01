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

    def split(self, text: str, max_paths: int = 5) -> SandhiSplitResult:
        """
        Segments a Sanskrit sentence into constituent words.
        Returns top candidate split alongside alternate interpretations.
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

        try:
            slp1_input = self._devanagari_to_slp1(clean_text)
            graph = self._analyzer.getSandhiSplits(SanskritNormalizedString(slp1_input))
            if graph:
                paths = graph.find_all_paths(max_paths=max_paths)
                for path in paths:
                    dev_words = [self._slp1_to_devanagari(str(w)) for w in path]
                    all_options.append(SandhiSplitOption(split_words=dev_words, confidence=0.95))

                if all_options:
                    final_splits = all_options[0].split_words
        except Exception as e:
            logger.warning(f"Sandhi splitting failed on '{text}': {e}. Falling back to tokenized words.")

        # Fallback: if graph found no paths, use space-delimited words
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

