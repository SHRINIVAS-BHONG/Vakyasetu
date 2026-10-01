from functools import lru_cache
import re
import unicodedata

class SanskritNormalizer:
    """
    Production-Optimized Sanskrit Text Sanitizer and Unicode Normalizer.
    Features:
    - Canonical Unicode NFC normalization.
    - Stripping of invisible zero-width characters (ZWNJ, ZWJ, BOM) that break dictionary lookups.
    - Whitespace normalization (collapsing multi-spaces, tabs, newlines to single space).
    - Preservation of the full Devanagari range (\u0900-\u097F), dandas (। and ॥), avagraha (ऽ),
      anusvara, visarga, and standard punctuation.
    - In-memory bounded LRU cache (4096 entries) for instant sub-microsecond retrieval of hot tokens.
    """

    # Invisible characters commonly introduced by PDF copying or mobile keyboards
    ZERO_WIDTH_PATTERN = re.compile(r"[\u200B-\u200D\uFEFF\u00A0]")
    # Multi-space collapse
    MULTI_SPACE_PATTERN = re.compile(r"\s+")
    # Allowed Sanskrit character set: Devanagari block (\u0900-\u097F), dandas, and sentence punctuation
    ALLOWED_CHARS_PATTERN = re.compile(r"[^\u0900-\u097F\s।॥.,?!;:\"'()-]")
    # Devanagari range check
    DEVANAGARI_RANGE_PATTERN = re.compile(r"[\u0900-\u097F]")

    @staticmethod
    @lru_cache(maxsize=4096)
    def normalize(text: str) -> str:
        """
        Normalizes and cleans Sanskrit text for high-reliability downstream processing.
        Cached via LRU for sub-microsecond repeated lookups.
        """
        if not text:
            return ""

        # Step 1: Strip invisible zero-width characters first
        cleaned = SanskritNormalizer.ZERO_WIDTH_PATTERN.sub("", text)

        # Step 2: Canonical Unicode NFC normalization
        normalized = unicodedata.normalize("NFC", cleaned.strip())

        # Step 3: Collapse whitespace
        collapsed = SanskritNormalizer.MULTI_SPACE_PATTERN.sub(" ", normalized)

        # Step 4: Filter out disallowed foreign symbols while strictly preserving Sanskrit characters
        sanitized = SanskritNormalizer.ALLOWED_CHARS_PATTERN.sub("", collapsed)

        return sanitized.strip()

    @staticmethod
    @lru_cache(maxsize=4096)
    def is_devanagari(text: str) -> bool:
        """
        Fast check verifying if the text contains genuine Sanskrit Devanagari glyphs.
        """
        if not text:
            return False
        return bool(SanskritNormalizer.DEVANAGARI_RANGE_PATTERN.search(text))

