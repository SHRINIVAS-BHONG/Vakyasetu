from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class MorphologicalGloss(BaseModel):
    """
    Detailed pedagogical breakdown for a single Sanskrit word token,
    translated from Paninian computational tags to CBSE/NCERT Class 6-10 syllabus.
    """
    root: str = Field(..., description="Base lemma or dhātu/prātipadika (e.g. गम्, पठ्, बालक)")
    pos: str = Field(..., description="Part of speech: Noun (नामपदम्), Verb (क्रियापदम्), Indeclinable (अव्ययम्), Pronoun (सर्वनाम)")
    gender: Optional[str] = Field(None, description="Masculine (पुंल्लिङ्गम्), Feminine (स्त्रीलिङ्गम्), Neuter (नपुंसकलिङ्गम्)")
    case: Optional[str] = Field(None, description="Vibhakti: Nominative (प्रथमा), Accusative (द्वितीया), etc.")
    number: Optional[str] = Field(None, description="Vacana: Singular (एकवचनम्), Dual (द्विवचनम्), Plural (बहुवचनम्)")
    tense: Optional[str] = Field(None, description="Lakāra: Present (लट्), Past (लङ्), Future (लृट्), Imperative (लोट्), Potential (विधिलिङ्)")
    person: Optional[str] = Field(None, description="Puruṣa: Third Person (प्रथमपुरुषः), Second Person (मध्यमपुरुषः), First Person (उत्तमपुरुषः)")
    prefix: Optional[str] = Field(None, description="Upasarga prefix if present (e.g. प्र, अनु, आ, वि)")
    pratyaya: Optional[str] = Field(None, description="Grammatical suffix/pratyaya (e.g. क्त्वा, तुमुन्, ल्यप्, शतृ, क्तवतु, मतुप्)")
    voice: Optional[str] = Field(None, description="Prayoga: Active Voice (कर्तरि प्रयोगः) or Passive Voice (कर्मणि प्रयोगः)")
    sanskrit_explanation: str = Field(..., description="Student-friendly summary in Devanagari")
    english_explanation: str = Field(..., description="Clear explanation in English for school learners")

class WordAnalysis(BaseModel):
    """Word-level analysis container with primary parse and candidate alternatives."""
    word: str = Field(..., description="Surface Sanskrit token from sandhi-split output")
    primary_gloss: MorphologicalGloss = Field(..., description="Top-ranked pedagogical gloss")
    alternative_glosses: List[MorphologicalGloss] = Field(default_factory=list, description="Alternative valid grammatical parses if ambiguous")
    is_compound: bool = Field(False, description="Whether this word is a compound constituent")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score of the morphological parse")

class SandhiSplitOption(BaseModel):
    """A single candidate sandhi split."""
    split_words: List[str] = Field(..., description="Ordered list of segmented tokens")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score of this split")

class AnalyzeRequest(BaseModel):
    """User request containing raw Sanskrit text."""
    text: str = Field(..., min_length=1, max_length=1500, description="Raw Sanskrit sentence entered by student")

class MorphologyRequest(BaseModel):
    """Direct request to analyze specific Sanskrit tokens."""
    tokens: List[str] = Field(..., min_length=1, description="List of pre-segmented Sanskrit words")

class AnalyzeResponse(BaseModel):
    """Unified response combining translation, sandhi segmentation, and morphological glosses."""
    original_text: str = Field(..., description="Original input entered by user")
    normalized_text: str = Field(..., description="Cleaned Unicode NFC text")
    translation: str = Field(..., description="Natural English translation from Satyam's IndicTrans2 model")
    sandhi_splits: List[str] = Field(..., description="Split words from Mayank's sandhi engine")
    all_sandhi_options: List[SandhiSplitOption] = Field(default_factory=list, description="Alternative sandhi segmentations")
    morphology: List[WordAnalysis] = Field(..., description="Word-level grammatical analysis from Shrinivas's engine")
    cached: bool = Field(False, description="True if response was retrieved from SQLite cache")
    processing_time_ms: float = Field(..., description="Total pipeline latency in milliseconds")

# Alias for Master Orchestration schema
VakyaSetuResponse = AnalyzeResponse

class HealthStatus(BaseModel):
    """Health and readiness check response."""
    status: str = Field("healthy", description="Overall system health")
    version: str = Field("1.0.0", description="Backend API version")
    python_version: str = Field(..., description="Runtime Python version")
    cache_connected: bool = Field(True, description="SQLite cache connectivity status")
    services: Dict[str, str] = Field(default_factory=dict, description="Status of internal services")
