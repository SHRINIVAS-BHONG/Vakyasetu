import unicodedata
import re

class SanskritNormalizer:
    """
    Production Unicode Normalization and Sanitization Engine for Sanskrit Text.
    Ensures input strings conform to canonical NFC representation, strips stray characters
    and anomalous whitespace, while strictly preserving Devanagari diacritics,
    virāma, anusvāra, visarga, avagraha, and traditional dandas (। and ॥).
    """

    # Allowed Sanskrit character set: Devanagari block (\u0900-\u097F), dandas, and basic sentence punctuation
    ALLOWED_CHARS_PATTERN = re.compile(r"[^\u0900-\u097F\s।॥.,?!;:\"'()-]")
    DEVANAGARI_RANGE_PATTERN = re.compile(r"[\u0900-\u097F]")

    @classmethod
    def normalize(cls, text: str) -> str:
        """
        Cleans and normalizes Sanskrit text:
        1. Strips leading and trailing whitespace.
        2. Normalizes into canonical Unicode NFC (Composed) form.
        3. Collapses multiple whitespace characters into a single space.
        4. Strips disallowed characters while preserving Devanagari, dandas, and punctuation.
        """
        if not text:
            return ""

        # Step 1 & 2: NFC normalization
        normalized = unicodedata.normalize("NFC", text.strip())

        # Step 3: Collapse whitespace
        collapsed = re.sub(r"\s+", " ", normalized)

        # Step 4: Remove stray characters not in Devanagari or allowed punctuation
        cleaned = cls.ALLOWED_CHARS_PATTERN.sub("", collapsed)

        # Trim again in case stripping left trailing spaces
        return cleaned.strip()

    @classmethod
    def is_devanagari(cls, text: str) -> bool:
        """
        Validates whether a given string contains genuine Devanagari characters.
        Useful for pre-flight input validation before triggering NLP pipelines.
        """
        if not text:
            return False
        return bool(cls.DEVANAGARI_RANGE_PATTERN.search(text))
