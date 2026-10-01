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
)
from app.services.cache import SQLiteCache, get_cache
from app.services.sandhi import SandhiService, get_sandhi_service
from app.services.morphology import MorphologyService, get_morphology_service
from app.services.translation import TranslationService, get_translation_service

logger = logging.getLogger(__name__)

class OrchestratorService:
    """
    Master Orchestration Engine for VākyaSetu.
    
    Seamlessly chains and synchronizes:
    1. SanskritNormalizer: Canonical Unicode NFC sanitization & zero-width character stripping.
    2. Two-Tier Cache Engine: Instant sub-millisecond retrieval on L1 RAM or L2 SQLite hit.
    3. SandhiService: Graph-based word segmentation using Sanskrit Heritage graphs.
    4. MorphologyService: Pedagogical Paninian-to-NCERT bilingual morphological parsing with deterministic fallback.
    5. TranslationService: Generative Kāraka syntactic translation and IndicTrans2 neural generation.
    """

    def __init__(
        self,
        cache: Optional[SQLiteCache] = None,
        sandhi_service: Optional[SandhiService] = None,
        morphology_service: Optional[MorphologyService] = None,
        translation_service: Optional[TranslationService] = None,
    ):
        self.cache = cache or get_cache()
        self.sandhi = sandhi_service or get_sandhi_service()
        self.morphology = morphology_service or get_morphology_service()
        self.translation = translation_service or get_translation_service()
        self.normalizer = SanskritNormalizer

    def analyze(self, text: str, bypass_cache: bool = False) -> VakyaSetuResponse:
        """
        Executes end-to-end linguistic analysis for a Sanskrit sentence.
        
        Execution Flow:
        1. Unicode normalization and zero-width character cleansing.
        2. Tier-1 (RAM) and Tier-2 (SQLite) cache lookup.
        3. Fused compound and sandhi segmentation.
        4. Word-by-word NCERT morphological glossing.
        5. Natural English syntax generation.
        6. Serialization into unified VakyaSetuResponse and cache persistence.
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
                morphology=[],
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

        # Step 2: Sandhi Splitting
        sandhi_result = self.sandhi.split(normalized)
        split_words = sandhi_result.split_words
        all_sandhi_options = sandhi_result.all_candidates

        # Step 3: Morphological Analysis
        morph_analyses: List[WordAnalysis] = self.morphology.analyze_tokens(split_words)

        # Step 4: Syntactic & Neural Translation
        translation: str = self.translation.translate(
            raw_sanskrit_sentence=normalized,
            morphology_analysis=morph_analyses
        )

        # Step 5: Construct Unified Response
        total_latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        response = VakyaSetuResponse(
            original_text=raw_text,
            normalized_text=normalized,
            translation=translation,
            sandhi_splits=split_words,
            all_sandhi_options=all_sandhi_options,
            morphology=morph_analyses,
            cached=False,
            processing_time_ms=total_latency_ms,
        )

        # Step 6: Persist into Two-Tier Cache
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
