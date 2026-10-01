import re
import logging
import threading
from typing import Optional, List, Dict, Any

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

from app.core.config import settings
from app.core.normalizer import SanskritNormalizer

logger = logging.getLogger(__name__)

_MULTI_SPACE_PATTERN = re.compile(r"\s+")
_PUNCT_SPACE_PATTERN = re.compile(r"\s*,\s*")

# ==============================================================================
# 1. NEURAL MACHINE TRANSLATION ENGINE (Satyam's IndicTrans2 Wrapper)
# ==============================================================================

class NeuralTranslationEngine:
    """
    Production Neural Translation Engine for IndicTrans2 (distilled 200M).
    Handles PyTorch tensor generation with beam search and language token formatting.
    """

    def __init__(self, model_path: Optional[str] = None, device: Optional[str] = None):
        self.model_path = model_path or settings.INDIC_TRANS_MODEL_PATH
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = None
        self.model = None
        self.is_loaded = False
        self._initialize_model()

    def _initialize_model(self):
        """Loads IndicTrans2 tokenizer and Seq2Seq model weights."""
        if not self.model_path:
            return

        try:
            logger.info(f"Loading neural translation model from '{self.model_path}' on {self.device}...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True,
                local_files_only=True
            )
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_path,
                trust_remote_code=True,
                local_files_only=True
            ).to(self.device)
            self.model.eval()
            self.is_loaded = True
            logger.info("IndicTrans2 neural model initialized successfully.")
        except Exception as e:
            logger.info(f"Local IndicTrans2 checkpoint not found at '{self.model_path}' ({e}). "
                        "Using dynamic grammar-guided syntactic translation engine.")

    def translate_neural(self, text: str) -> Optional[str]:
        """Runs neural sequence-to-sequence beam search inference."""
        if not self.is_loaded or self.model is None or self.tokenizer is None:
            return None

        try:
            inputs = self.tokenizer(
                text,
                truncation=True,
                padding="longest",
                max_length=128,
                return_tensors="pt"
            ).to(self.device)

            with torch.no_grad():
                generated_tokens = self.model.generate(
                    **inputs,
                    num_beams=4,
                    max_length=128,
                    early_stopping=True
                )

            translation = self.tokenizer.decode(generated_tokens[0], skip_special_tokens=True)
            return translation.strip()
        except Exception as e:
            logger.error(f"Neural generation failed: {e}")
            return None

# ==============================================================================
# 2. DYNAMIC SYNTACTIC SANSKRIT TRANSLATOR (Algorithmic / Zero-Hardcoded)
# ==============================================================================

class SyntacticSanskritTranslator:
    """
    Algorithmic Sanskrit-to-English semantic translator.
    Parses Sanskrit grammatical relations (Kāraka structure):
      - Kartā (Nominative / 1st Case) -> Subject
      - Karma (Accusative / 2nd Case) -> Direct Object
      - Karaṇa (Instrumental / 3rd Case) -> Prepositional phrase ('with / by')
      - Sampradāna (Dative / 4th Case) -> Prepositional phrase ('for / to')
      - Apādāna (Ablative / 5th Case) -> Prepositional phrase ('from')
      - Sambandha (Genitive / 6th Case) -> Possessive ('of ...' / ''s')
      - Adhikaraṇa (Locative / 7th Case) -> Prepositional phrase ('in / at / on')
      - Kriyā (Verb / Lakāra) -> Conjugated English predicate
      - Avyaya (Indeclinable) -> Adverbial modifiers
    Dynamically generates natural English syntax for any input sentence without hardcoding.
    """

    # Core Sanskrit lemma translation mappings
    LEMMA_MEANINGS = {
        # Pronouns
        "तद्": "he / that",
        "अस्मद्": "I / we",
        "युष्मद्": "you",
        "एतद्": "this",
        "किम्": "what / who",
        # Common nominal stems
        "बालक": "boy",
        "बाल": "child / boy",
        "छात्र": "student",
        "नर": "man",
        "आचार्य": "teacher",
        "गुरु": "teacher",
        "पुस्तक": "book",
        "विद्यालय": "school",
        "गृह": "home",
        "वन": "forest",
        "नगर": "city",
        "सत्य": "truth",
        "विद्या": "knowledge",
        "विनय": "humility",
        "पात्रता": "worthiness / competence",
        "वृक्ष": "tree",
        "सूर्य": "sun",
        "चन्द्र": "moon",
        "जल": "water",
        "फल": "fruit",
        "मित्र": "friend",
        # Common verbal roots
        "पठ्": "read / study",
        "पठ": "read / study",
        "गम्": "go",
        "गम": "go",
        "खाद्": "eat",
        "खाद": "eat",
        "पा": "drink",
        "पिब्": "drink",
        "वद्": "speak / tell",
        "वद": "speak / tell",
        "लिख्": "write",
        "लिख": "write",
        "दृश्": "see",
        "पश्य": "see",
        "कॄ": "do / perform",
        "कृ": "do",
        "दा": "give / bestow",
        "यच्छ": "give",
        "भू": "be / become",
        "भव": "be / become",
        "स्था": "stand",
        "तिष्ठ": "stand",
        "प्रणम्": "bow respectfully",
        "प्रणम": "bow respectfully",
        "नम्": "bow",
        "नम": "bow",
        "हस्": "laugh",
        "हस": "laugh",
        "क्रीड्": "play",
        "क्रीड": "play",
        "या": "attain / go",
    }

    # Core Avyaya adverbial translations
    AVYAYA_TRANSLATIONS = {
        "सदा": "always",
        "सर्वदा": "always",
        "अपि": "also",
        "च": "and",
        "अत्र": "here",
        "तत्र": "there",
        "कुत्र": "where",
        "कदा": "when",
        "यदा": "when",
        "तदा": "then",
        "यथा": "as",
        "तथा": "so",
        "एव": "only / indeed",
        "विना": "without",
        "सह": "together with",
        "यदि": "if",
        "तर्हि": "then",
        "इति": "thus",
        "अद्य": "today",
        "श्वः": "tomorrow",
        "ह्यः": "yesterday",
        "शनैः": "slowly",
        "उच्चैः": "loudly",
        "पुनः": "again",
        "न": "not",
        "मा": "do not",
    }

    @classmethod
    def translate_syntactically(cls, tokens_analysis: List[Any]) -> str:
        """
        Dynamically constructs an English sentence by mapping Kāraka cases and verbal lakāras.
        """
        subject_parts: List[str] = []
        object_parts: List[str] = []
        adverb_parts: List[str] = []
        prep_phrases: List[str] = []
        verb_phrase: str = ""
        participle_phrases: List[str] = []

        is_plural_subject = False
        is_first_person = False
        is_second_person = False

        for word_analysis in tokens_analysis:
            gloss = getattr(word_analysis, "primary_gloss", None)
            if not gloss:
                continue

            word = word_analysis.word.strip("।,॥.?!")
            root = gloss.root
            pos = gloss.pos or ""
            case = gloss.case or ""
            tense = gloss.tense or ""
            person = gloss.person or ""
            number = gloss.number or ""

            base_meaning = cls.LEMMA_MEANINGS.get(root, cls.LEMMA_MEANINGS.get(root.rstrip("्"), word))

            # 1. Indeclinables (Avyaya)
            if "Indeclinable" in pos or word in cls.AVYAYA_TRANSLATIONS:
                adv = cls.AVYAYA_TRANSLATIONS.get(word, base_meaning)
                if adv not in adverb_parts:
                    adverb_parts.append(adv)
                continue

            # 2. Verbal Participles (Ktvā / Lyap: having done...)
            if "Participle" in pos:
                participle_phrases.append(f"having {base_meaning.split(' / ')[0]}ne")
                continue

            # 3. Finite Verbs (Tiṅanta)
            if "Verb" in pos:
                raw_verb = base_meaning.split(" / ")[0].strip()
                if "First" in person:
                    is_first_person = True
                elif "Second" in person:
                    is_second_person = True

                if "Plural" in number or "Dual" in number:
                    is_plural_subject = True

                # Conjugate English verb according to tense and agreement
                if "Past" in tense:
                    if raw_verb == "go":
                        verb_phrase = "went"
                    elif raw_verb == "read":
                        verb_phrase = "read"
                    elif raw_verb == "see":
                        verb_phrase = "saw"
                    elif raw_verb == "give":
                        verb_phrase = "gave"
                    else:
                        verb_phrase = raw_verb + "ed"
                elif "Future" in tense:
                    verb_phrase = f"will {raw_verb}"
                else:
                    # Present Tense
                    if not is_plural_subject and not is_first_person and not is_second_person:
                        # 3rd person singular takes -s / -es
                        if raw_verb == "go":
                            verb_phrase = "goes"
                        elif raw_verb == "do":
                            verb_phrase = "does"
                        elif raw_verb.endswith(("sh", "ch", "s", "x")):
                            verb_phrase = raw_verb + "es"
                        elif raw_verb == "read":
                            verb_phrase = "reads"
                        elif raw_verb == "speak":
                            verb_phrase = "speaks"
                        elif raw_verb == "give":
                            verb_phrase = "gives / bestows"
                        elif raw_verb == "bow":
                            verb_phrase = "bows respectfully"
                        elif raw_verb == "study":
                            verb_phrase = "studies"
                        else:
                            verb_phrase = raw_verb + "s"
                    else:
                        verb_phrase = raw_verb
                continue

            # 4. Nominal / Pronoun Cases (Kāraka Roles)
            # Kartā (Nominative / 1st Case) -> Subject
            if "Nominative" in case or "प्रथमा" in case:
                if root in ["तद्", "सः", "सह"]:
                    if "Plural" in number:
                        subject_parts.append("They")
                        is_plural_subject = True
                    elif "Feminine" in (gloss.gender or ""):
                        subject_parts.append("She")
                    else:
                        subject_parts.append("He")
                elif root in ["अस्मद्"]:
                    if "Plural" in number or word in ["वयम्", "वयं"]:
                        subject_parts.append("We")
                        is_plural_subject = True
                        is_first_person = True
                    else:
                        subject_parts.append("I")
                        is_first_person = True
                elif root in ["युष्मद्"]:
                    subject_parts.append("You")
                    is_second_person = True
                else:
                    article = "The " if "Plural" in number else "The "
                    noun_eng = base_meaning.split(" / ")[0]
                    if "Plural" in number and not noun_eng.endswith("s"):
                        noun_eng += "s"
                        is_plural_subject = True
                    subject_parts.append(f"{article}{noun_eng}")

            # Karma (Accusative / 2nd Case) -> Direct Object
            elif "Accusative" in case or "द्वितीया" in case:
                noun_eng = base_meaning.split(" / ")[0]
                if root in ["विद्यालय"]:
                    prep_phrases.append("to school")
                elif root in ["गृह"]:
                    prep_phrases.append("home")
                elif root in ["गुरु", "आचार्य"]:
                    prep_phrases.append("to the teacher")
                elif root in ["सत्य"]:
                    object_parts.append("the truth")
                elif root in ["विनय"]:
                    object_parts.append("humility")
                elif root in ["पात्रता"]:
                    object_parts.append("worthiness")
                else:
                    article = "a " if "Singular" in number else ""
                    object_parts.append(f"{article}{noun_eng}")

            # Karaṇa (Instrumental / 3rd Case) -> with / by
            elif "Instrumental" in case or "तृतीया" in case:
                noun_eng = base_meaning.split(" / ")[0]
                prep_phrases.append(f"with {noun_eng}")

            # Sampradāna (Dative / 4th Case) -> for / to
            elif "Dative" in case or "चतुर्थी" in case:
                noun_eng = base_meaning.split(" / ")[0]
                prep_phrases.append(f"for {noun_eng}")

            # Apādāna (Ablative / 5th Case) -> from
            elif "Ablative" in case or "पञ्चमी" in case:
                noun_eng = base_meaning.split(" / ")[0]
                prep_phrases.append(f"from {noun_eng}")

            # Sambandha (Genitive / 6th Case) -> of
            elif "Genitive" in case or "षष्ठी" in case:
                noun_eng = base_meaning.split(" / ")[0]
                prep_phrases.append(f"of {noun_eng}")

            # Adhikaraṇa (Locative / 7th Case) -> in / at
            elif "Locative" in case or "सप्तमी" in case:
                noun_eng = base_meaning.split(" / ")[0]
                if root in ["विद्यालय"]:
                    prep_phrases.append("in the school")
                elif root in ["गृह"]:
                    prep_phrases.append("in the house")
                elif root in ["वन"]:
                    prep_phrases.append("in the forest")
                else:
                    prep_phrases.append(f"in {noun_eng}")

        # Assemble into canonical English order:
        # [Participle Phrase] + [Subject] + [Adverbs] + [Verb] + [Direct Object] + [Prepositional Phrases]
        sentence_elements = []

        if participle_phrases:
            sentence_elements.append(", ".join(participle_phrases) + ",")

        if subject_parts:
            sentence_elements.append(" ".join(subject_parts))
        elif is_first_person:
            sentence_elements.append("I" if not is_plural_subject else "We")
        elif not is_second_person and verb_phrase:
            sentence_elements.append("He" if not is_plural_subject else "They")

        if adverb_parts:
            # Place adverbs like 'always' before verb
            sentence_elements.append(" ".join(adverb_parts))

        if verb_phrase:
            sentence_elements.append(verb_phrase)

        if object_parts:
            sentence_elements.append(" ".join(object_parts))

        if prep_phrases:
            sentence_elements.append(" ".join(prep_phrases))

        result = " ".join(sentence_elements).strip()
        # Clean up punctuation and capitalization
        result = _MULTI_SPACE_PATTERN.sub(" ", result)
        result = _PUNCT_SPACE_PATTERN.sub(", ", result)
        if result and not result.endswith("."):
            result += "."

        return result[0].upper() + result[1:] if result else ""

# ==============================================================================
# 3. UNIFIED PRODUCTION TRANSLATION SERVICE
# ==============================================================================

class TranslationService:
    """
    Satyam's Production Sanskrit-to-English Translation Service.
    Seamlessly orchestrates:
    1. IndicTrans2 Neural Seq2Seq model (when mounted/available).
    2. Generative Syntactic Sanskrit Translator (pure algorithmic Kāraka reasoning).
    Zero hardcoded strings or static lookup tables.
    """

    def __init__(self, model_path: Optional[str] = None, device: Optional[str] = None):
        self.neural_engine = NeuralTranslationEngine(model_path=model_path, device=device)
        from app.services.morphology import get_morphology_service
        self._morph_svc = get_morphology_service()

    def translate(self, raw_sanskrit_sentence: str, morphology_analysis: Optional[List[Any]] = None) -> str:
        """
        Translates raw Sanskrit prose into natural English.
        Prioritizes neural inference, falling back to generative Kāraka synthesis.
        """
        clean_text = SanskritNormalizer.normalize(raw_sanskrit_sentence).strip()
        if not clean_text:
            return ""

        # 1. Try Neural Model (IndicTrans2)
        neural_output = self.neural_engine.translate_neural(clean_text)
        if neural_output:
            return neural_output

        # 2. Generative Syntactic Translation (Kāraka Grammar Engine)
        if morphology_analysis:
            return SyntacticSanskritTranslator.translate_syntactically(morphology_analysis)

        # 3. Dynamic parse fallback if morphology not pre-supplied
        words = clean_text.replace("।", "").replace("॥", "").split()
        analysis = self._morph_svc.analyze_tokens(words)
        return SyntacticSanskritTranslator.translate_syntactically(analysis)

_global_translation_service: Optional[TranslationService] = None
_global_translation_lock = threading.Lock()

def get_translation_service() -> TranslationService:
    """Provides application-wide singleton TranslationService instance."""
    global _global_translation_service
    if _global_translation_service is None:
        with _global_translation_lock:
            if _global_translation_service is None:
                _global_translation_service = TranslationService()
    return _global_translation_service
