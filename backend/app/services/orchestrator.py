import logging
import time
import threading
from typing import Optional, Dict, Any, List

from app.core.normalizer import SanskritNormalizer
from app.models.schemas import (
    VakyaSetuResponse,
    AnalyzeResponse,
    WordAnalysis,
    SandhiSplitOption,
    SandhiRuleExplanation,
    SamasaAnalysis,
    KarakaRelation,
    GrammarIssue,
)
from app.services.cache import SQLiteCache, get_cache
from app.services.sandhi import SandhiService, get_sandhi_service
from app.services.morphology import MorphologyService, get_morphology_service
from app.services.translation import TranslationService, get_translation_service
from app.services.samasa import SamasaService, get_samasa_service
from app.services.grammar_validator import GrammarValidator

logger = logging.getLogger(__name__)

class OrchestratorService:
    """
    Master Orchestration Engine for VākyaSetu.
    
    Seamlessly chains and synchronizes:
    1. SanskritNormalizer: Canonical Unicode NFC sanitization & zero-width character stripping.
    2. Two-Tier Cache Engine: Instant sub-millisecond retrieval on L1 RAM or L2 SQLite hit.
    3. SandhiService: Graph-based word segmentation and Paninian Sūtra rule identification (P3).
    4. MorphologyService: Pedagogical Paninian-to-NCERT bilingual morphological parsing with
       contextual disambiguation (P1) and Upapada-Vibhakti governance (P2).
    5. SamasaService: CBSE/NCERT Class 9-10 compound decomposition and Vigraha-vākya generation (P4).
    6. Anvaya Engine: Syntactic prose re-ordering from poetic/inverted word order (P5).
    7. TranslationService: Generative Kāraka syntactic translation and IndicTrans2 neural generation.
    """

    def __init__(
        self,
        cache: Optional[SQLiteCache] = None,
        sandhi_service: Optional[SandhiService] = None,
        morphology_service: Optional[MorphologyService] = None,
        translation_service: Optional[TranslationService] = None,
        samasa_service: Optional[SamasaService] = None,
    ):
        self.cache = cache or get_cache()
        self.sandhi = sandhi_service or get_sandhi_service()
        self.morphology = morphology_service or get_morphology_service()
        self.translation = translation_service or get_translation_service()
        self.samasa = samasa_service or get_samasa_service()
        self.normalizer = SanskritNormalizer

    @staticmethod
    def _generate_anvaya(morph_analyses: List[WordAnalysis]) -> List[str]:
        """
        P5: Paninian Pedagogical Anvaya (अन्वय-रचना) Generator.
        Re-orders poetic or inverted Sanskrit words into logical canonical prose reading order:
        [सम्बोधन/अव्यय] -> [विशेषण + कर्ता] -> [अधिकरण/अपादान/करण/सम्प्रदान] -> [विशेषण + कर्म] -> [कृदन्त] -> [क्रियाविशेषण] -> [क्रियापदम्]
        """
        if not morph_analyses:
            return []

        def _anvaya_rank(word_analysis: WordAnalysis) -> int:
            g = word_analysis.primary_gloss
            case = g.case or ""
            pos = g.pos or ""
            pratyaya = g.pratyaya or ""
            clean = word_analysis.word.strip("।,॥.?!")

            if clean in ["हे", "भोः", "अयि"] or "Vocative" in case or "सम्बोधन" in case:
                return 10
            if clean in ["यदि", "यदा", "चेत्", "अथ", "अपि"]:
                return 15

            # Subject (Kartā)
            if word_analysis.karaka_role and "कर्ता" in word_analysis.karaka_role:
                return 30
            if "Nominative" in case:
                return 30

            # Modifiers (Kārakas 7, 5, 3, 4, 6)
            if "Locative" in case or "सप्तमी" in case:
                return 40
            if "Ablative" in case or "पञ्चमी" in case:
                return 50
            if "Instrumental" in case or "तृतीया" in case:
                return 60
            if "Dative" in case or "चतुर्थी" in case:
                return 70
            if "Genitive" in case or "षष्ठी" in case:
                return 75

            # Object (Karma)
            if word_analysis.karaka_role and "कर्म" in word_analysis.karaka_role:
                return 90
            if "Accusative" in case:
                return 90

            # Participles (असमापिका क्रिया)
            if pratyaya in ["ktvA", "lyap", "tumun", "Satf", "Sanac"]:
                return 100

            # Adverbs / Negations immediately preceding verb
            if clean in ["न", "मा", "नहि", "सदा", "सर्वदा", "सहसा", "मन्दम्", "शीघ्रम्", "एव"]:
                return 110

            # Finite verb predicate (समापिका क्रिया)
            if pos.startswith("Verb") and g.tense:
                return 120

            return 85

        # Stable sort preserving original relative sequence for identical ranks
        sorted_tokens = sorted(
            [w for w in morph_analyses if w.word.strip("।,॥.?!")],
            key=_anvaya_rank
        )
        anvaya_words = [w.word.strip("।,॥.?!") for w in sorted_tokens if w.word.strip("।,॥.?!")]
        return anvaya_words

    def analyze(self, text: str, bypass_cache: bool = False) -> VakyaSetuResponse:
        """
        Executes end-to-end linguistic analysis for a Sanskrit sentence.
        
        Execution Flow:
        1. Unicode normalization and zero-width character cleansing.
        2. Tier-1 (RAM) and Tier-2 (SQLite) cache lookup.
        3. Sandhi segmentation & Paninian Sūtra rule identification (P3).
        4. Word-by-word NCERT morphological glossing + Contextual Disambiguation (P1) + Upapada Rules (P2).
        5. Samāsa compound decomposition and Vigraha generation (P4).
        6. Anvaya prose re-ordering (P5).
        7. Natural English syntax generation.
        8. Serialization into unified VakyaSetuResponse and cache persistence.
        """
        t0 = time.perf_counter()
        raw_text = text or ""
        normalized = self.normalizer.normalize(raw_text)

        if not normalized:
            return VakyaSetuResponse(
                original_text=raw_text,
                normalized_text="",
                translation="",
                sandhi_splits=[],
                all_sandhi_options=[],
                sandhi_rules=[],
                morphology=[],
                compounds=[],
                karaka_relations=[],
                anvaya=[],
                grammar_warnings=[],
                cached=False,
                processing_time_ms=0.0,
            )

        # Step 1: Check Two-Tier Cache (L1 RAM -> L2 SQLite WAL)
        if not bypass_cache:
            cached_data = self.cache.get(normalized)
            if cached_data is not None:
                latency_ms = (time.perf_counter() - t0) * 1000
                cached_data_copy = dict(cached_data)
                cached_data_copy["cached"] = True
                cached_data_copy["processing_time_ms"] = round(latency_ms, 2)
                try:
                    return VakyaSetuResponse(**cached_data_copy)
                except Exception as e:
                    logger.warning(f"Error deserializing cached payload: {e}. Recomputing.")

        # Step 2: Sandhi Splitting & Rule Identification (P3)
        sandhi_result = self.sandhi.split(normalized)
        split_words = sandhi_result.split_words
        all_sandhi_options = sandhi_result.all_candidates
        sandhi_rules: List[SandhiRuleExplanation] = sandhi_result.rules

        # Step 3: Morphological Analysis + Contextual Disambiguation (P1) + Upapada Rules (P2)
        raw_morph = [self.morphology.analyze_word(w) for w in split_words if w.strip()]
        morph_analyses, karaka_relations = self.morphology.disambiguate_and_extract_karakas(raw_morph)

        # Step 4: Samāsa Compound Decomposition (P4)
        detected_compounds: List[SamasaAnalysis] = []
        for word_analysis in morph_analyses:
            # Paninian rule: Samāsa is strictly nominal/indeclinable (सुबन्त / अव्यय),
            # never finite conjugated verbs (तिङन्त क्रियापदम्).
            if word_analysis.primary_gloss and "Verb" in (word_analysis.primary_gloss.pos or ""):
                continue
            comp_info = self.samasa.analyze_compound(word_analysis.word)
            if comp_info:
                word_analysis.samasa_info = comp_info
                word_analysis.is_compound = True
                detected_compounds.append(comp_info)

        # Step 5: Anvaya Prose Re-ordering (P5)
        anvaya: List[str] = self._generate_anvaya(morph_analyses)

        # Step 6: Syntactic & Neural Translation
        translation: str = self.translation.translate(
            raw_sanskrit_sentence=normalized,
            morphology_analysis=morph_analyses
        )

        # Step 7: Pedagogical Grammar Validation (Phase 8 / P1)
        grammar_warnings: List[GrammarIssue] = GrammarValidator.validate(
            morph_analyses=morph_analyses,
            karaka_relations=karaka_relations,
            raw_text=normalized
        )

        # Step 8: Construct Unified Response
        total_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        response = VakyaSetuResponse(
            original_text=raw_text,
            normalized_text=normalized,
            translation=translation,
            sandhi_splits=split_words,
            all_sandhi_options=all_sandhi_options,
            sandhi_rules=sandhi_rules,
            morphology=morph_analyses,
            compounds=detected_compounds,
            karaka_relations=karaka_relations,
            anvaya=anvaya,
            grammar_warnings=grammar_warnings,
            cached=False,
            processing_time_ms=total_latency_ms,
        )

        # Step 9: Persist into Two-Tier Cache
        try:
            cache_payload = response.model_dump()
            cache_payload["cached"] = False  # Stored state indicates source data
            self.cache.set(normalized, cache_payload)
        except Exception as e:
            logger.error(f"Failed to cache synthesized response for '{normalized}': {e}", exc_info=True)

        return response

    def get_telemetry(self) -> Dict[str, Any]:
        """Provides holistic operational metrics across all integrated subsystems."""
        cache_stats = self.cache.get_stats()
        return {
            "status": "operational",
            "cache": cache_stats,
            "neural_model_loaded": self.translation.neural_engine.is_loaded,
            "neural_device": self.translation.neural_engine.device,
        }

_global_orchestrator: Optional[OrchestratorService] = None
_global_orchestrator_lock = threading.Lock()

def get_orchestrator_service() -> OrchestratorService:
    """Provides application-wide singleton OrchestratorService instance."""
    global _global_orchestrator
    if _global_orchestrator is None:
        with _global_orchestrator_lock:
            if _global_orchestrator is None:
                _global_orchestrator = OrchestratorService()
    return _global_orchestrator
