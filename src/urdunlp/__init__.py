"""urdu-nlp-toolkit - Urdu and Roman Urdu text processing.

Pure Python, no dependencies, no model downloads.

    >>> from urdunlp import normalize, transliterate_to_urdu
    >>> normalize("كتاب")
    'کتاب'
    >>> transliterate_to_urdu("main theek hoon")
    'میں ٹھیک ہوں'
"""

from .normalize import is_urdu, normalize, remove_urls_and_mentions, resolve_arabic_heh
from .stopwords import NEGATION, STOPWORDS, is_stopword, remove_stopwords
from .tokenize import character_ngrams, fix_spacing, sentences, words
from .translit import (
    transliterate_to_roman,
    transliterate_to_urdu,
    transliterate_with_confidence,
)

__version__ = "0.1.0"

__all__ = [
    "NEGATION",
    "STOPWORDS",
    "character_ngrams",
    "fix_spacing",
    "is_stopword",
    "is_urdu",
    "normalize",
    "remove_stopwords",
    "remove_urls_and_mentions",
    "resolve_arabic_heh",
    "sentences",
    "transliterate_to_roman",
    "transliterate_to_urdu",
    "transliterate_with_confidence",
    "words",
]
