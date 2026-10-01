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

class SandhiRuleExplanation(BaseModel):
    """Paninian sandhi rule identification for a split boundary."""
    junction: str = Field(..., description="The phonetic junction where sandhi took place")
    rule_name: str = Field(..., description="Sanskrit name of the Sandhi rule (e.g. 'दीर्घसन्धिः', 'गुणसन्धिः')")
    sutra: str = Field(..., description="Classical Paninian Ashtadhyayi Sutra (e.g. 'अकः सवर्णे दीर्घः ६.१.१०१')")
    sandhi_type: str = Field(..., description="Category: स्वरसन्धिः (Vowel), व्यञ्जनसन्धिः (Consonant), or विसर्गसन्धिः (Visarga)")
    explanation: str = Field(..., description="Student-friendly pedagogical explanation")

class SamasaAnalysis(BaseModel):
    """CBSE/NCERT Class 9-10 Samāsa (compound) decomposition."""
    compound_word: str = Field(..., description="Original compound word (समस्तपदम्)")
    samasa_type: str = Field(..., description="Type of compound: तत्पुरुषः, कर्मधारयः, बहुव्रीहिः, द्वन्द्वः, अव्ययीभावः, द्विगुः")
    vigraha_vakya: str = Field(..., description="Analytical expansion / dissolution in Sanskrit (विग्रहवाक्यम्)")
    components: List[str] = Field(default_factory=list, description="Constituent words of the compound")
    explanation: str = Field(..., description="Pedagogical meaning of the compound")

class KarakaRelation(BaseModel):
    """Grammatical relation between words in the sentence (Ākāṅkṣā / Syntactic relation)."""
    source_word: str = Field(..., description="Dependent word (e.g. subject, object, instrument)")
    target_word: str = Field(..., description="Governing word (e.g. verb, preposition, head noun)")
    relation: str = Field(..., description="Kāraka role: कर्ता (Subject), कर्म (Object), करणम् (Instrument), सम्प्रदानम् (Recipient), अपादानम् (Source), सम्बन्धः (Possessive), अधिकरणम् (Location), उपपद-सम्बन्धः (Governed particle)")
    vibhakti: str = Field(..., description="Associated case (प्रथमा, द्वितीया, etc.)")
    rule: Optional[str] = Field(None, description="Grammar rule / justification (e.g. 'कर्तरि प्रथमा', 'सहयोगे तृतीया')")

class WordAnalysis(BaseModel):
    """Word-level analysis container with primary parse and candidate alternatives."""
    word: str = Field(..., description="Surface Sanskrit token from sandhi-split output")
    primary_gloss: MorphologicalGloss = Field(..., description="Top-ranked pedagogical gloss")
    alternative_glosses: List[MorphologicalGloss] = Field(default_factory=list, description="Alternative valid grammatical parses if ambiguous")
    is_compound: bool = Field(False, description="Whether this word is a compound constituent")
    samasa_info: Optional[SamasaAnalysis] = Field(None, description="Compound breakdown if the word is a compound")
    karaka_role: Optional[str] = Field(None, description="Assigned Kāraka syntactic role in sentence context")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score of the morphological parse")

class SandhiSplitOption(BaseModel):
    """A single candidate sandhi split."""
    split_words: List[str] = Field(..., description="Ordered list of segmented tokens")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score of this split")

class AnalyzeRequest(BaseModel):
    """User request containing raw Sanskrit text."""
    text: str = Field(..., min_length=1, max_length=1500, description="Raw Sanskrit sentence entered by student")

class BatchAnalyzeRequest(BaseModel):
    """Batch request containing multiple Sanskrit sentences."""
    sentences: List[str] = Field(..., min_length=1, max_length=50, description="List of Sanskrit sentences to analyze concurrently")

class BatchAnalyzeResponse(BaseModel):
    """Consolidated response for concurrent batch linguistic analysis."""
    results: List["AnalyzeResponse"] = Field(..., description="Ordered list of analysis results for each sentence")
    total_sentences: int = Field(..., description="Number of sentences processed")
    total_processing_time_ms: float = Field(..., description="Cumulative wall-clock latency for the batch in milliseconds")

class MorphologyRequest(BaseModel):
    """Direct request to analyze specific Sanskrit tokens."""
    tokens: List[str] = Field(..., min_length=1, description="List of pre-segmented Sanskrit words")

class GrammarIssue(BaseModel):
    """Pedagogical warning or error identified in student sentence construction."""
    issue_type: str = Field(..., description="Classification: SUBJECT_VERB_PERSON_MISMATCH, SUBJECT_VERB_NUMBER_MISMATCH, ADJECTIVE_NOUN_CONCORDANCE, UPAPADA_CASE_VIOLATION, etc.")
    severity: str = Field("warning", description="Severity level: error, warning, or suggestion")
    erroneous_token: str = Field(..., description="The word or junction causing the grammatical issue")
    sanskrit_explanation: str = Field(..., description="Explanation of the grammatical rule in Sanskrit/Hindi")
    english_explanation: str = Field(..., description="Clear constructive explanation in English for students")
    suggested_correction: Optional[str] = Field(None, description="Suggested correction or standard textbook replacement")

class AnalyzeResponse(BaseModel):
    """Unified response combining translation, sandhi segmentation, and morphological glosses."""
    original_text: str = Field(..., description="Original input entered by user")
    normalized_text: str = Field(..., description="Cleaned Unicode NFC text")
    translation: str = Field(..., description="Natural English translation from Satyam's IndicTrans2 model")
    sandhi_splits: List[str] = Field(..., description="Split words from Mayank's sandhi engine")
    all_sandhi_options: List[SandhiSplitOption] = Field(default_factory=list, description="Alternative sandhi segmentations")
    sandhi_rules: List[SandhiRuleExplanation] = Field(default_factory=list, description="Paninian sandhi sutras and rule names for split junctions")
    morphology: List[WordAnalysis] = Field(..., description="Word-level grammatical analysis from Shrinivas's engine")
    compounds: List[SamasaAnalysis] = Field(default_factory=list, description="Samāsa decompositions, classifications, and vigraha-vākya")
    karaka_relations: List[KarakaRelation] = Field(default_factory=list, description="Syntactic Kāraka dependencies and agreement links")
    anvaya: List[str] = Field(default_factory=list, description="Syntactically ordered prose reading sequence (अन्वय)")
    grammar_warnings: List[GrammarIssue] = Field(default_factory=list, description="Pedagogical grammar warnings, agreement errors, or suggested corrections for student compositions")
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
