import logging
from dataclasses import dataclass
from typing import List, Tuple

from indic_transliteration import sanscript
from sanskrit_parser.base.sanskrit_base import SanskritNormalizedString
from sanskrit_parser.parser.sandhi_analyzer import LexicalSandhiAnalyzer

from app.models.schemas import SandhiSplitOption

logger = logging.getLogger(__name__)

@dataclass
class SandhiSplitResult:
    split_words: List[str]
    confidence: float
    all_candidates: List[SandhiSplitOption]

class SandhiService:
    """
    Mayank's Sandhi Splitting Engine for VākyaSetu.
    Uses the Sanskrit Heritage Reader sandhi graphs to separate fused words and compounds.
    """

    def __init__(self):
        self._analyzer = LexicalSandhiAnalyzer()

    @staticmethod
    def _devanagari_to_slp1(devanagari_text: str) -> str:
        return sanscript.transliterate(devanagari_text, sanscript.DEVANAGARI, sanscript.SLP1)

    @staticmethod
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
        clean_text = text.strip("।,॥.?!")
        if not clean_text:
            return SandhiSplitResult(split_words=[], confidence=1.0, all_candidates=[])

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

        return SandhiSplitResult(
            split_words=final_splits,
            confidence=all_options[0].confidence if all_options else 0.85,
            all_candidates=all_options
        )
