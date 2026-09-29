"""Readability formulas, one function per published formula.

References
- Flesch, R. (1948). A new readability yardstick. Journal of Applied Psychology 32(3).
    Reading Ease = 206.835 - 1.015*(words/sentences) - 84.6*(syllables/words)
- Kincaid, J. P., Fishburne, R. P., Rogers, R. L., Chissom, B. S. (1975).
    Derivation of new readability formulas for Navy enlisted personnel.
    Grade level = 0.39*(words/sentences) + 11.8*(syllables/words) - 15.59
- Kandel, L. & Moles, A. (1958). Application de l'indice de Flesch a la langue
    francaise. Cahiers Etudes de Radio-Television 19.
    Score = 207 - 1.015*(words/sentences) - 73.6*(syllables/words)
- Fernandez Huerta, J. (1959). Medidas sencillas de lecturabilidad. Consigna 214.
    Score = 206.84 - 0.60*(syllables per 100 words) - 1.02*(sentences per 100 words)
- Szigriszt Pazos, F. (1993). Sistemas predictivos de legibilidad del mensaje
    escrito: formula de perspicuidad. Universidad Complutense de Madrid.
    Score = 206.835 - 62.3*(syllables/words) - (words/sentences)
"""
from __future__ import annotations

# The score used by --min-score for each language.
PRIMARY = {"en": "flesch_reading_ease", "fr": "kandel_moles", "es": "fernandez_huerta"}


def flesch_reading_ease(words: int, sentences: int, syllables: int) -> float:
    return 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)


def flesch_kincaid_grade(words: int, sentences: int, syllables: int) -> float:
    return 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59


def kandel_moles(words: int, sentences: int, syllables: int) -> float:
    return 207 - 1.015 * (words / sentences) - 73.6 * (syllables / words)


def fernandez_huerta(words: int, sentences: int, syllables: int) -> float:
    return 206.84 - 0.60 * (syllables * 100 / words) - 1.02 * (sentences * 100 / words)


def szigriszt_pazos(words: int, sentences: int, syllables: int) -> float:
    return 206.835 - 62.3 * (syllables / words) - (words / sentences)


def sentence_grade(words: int, syllables: int) -> float:
    """Flesch-Kincaid grade of a single sentence; only used to rank the hardest ones."""
    return flesch_kincaid_grade(words, 1, syllables)


# Interpretation bands: (lower bound inclusive, label), highest first.
_FLESCH_BANDS = [
    (90, "very easy"), (80, "easy"), (70, "fairly easy"), (60, "plain language"),
    (50, "fairly difficult"), (30, "difficult"), (float("-inf"), "very difficult"),
]
BANDS = {
    "flesch_reading_ease": _FLESCH_BANDS,
    "kandel_moles": _FLESCH_BANDS,  # same 0-100 scale as Flesch
    "fernandez_huerta": [
        (90, "very easy"), (80, "easy"), (70, "fairly easy"), (60, "normal"),
        (50, "fairly difficult"), (30, "difficult"), (float("-inf"), "very difficult"),
    ],
    "szigriszt_pazos": [  # INFLESZ scale
        (80, "very easy"), (65, "fairly easy"), (55, "normal"),
        (40, "somewhat difficult"), (float("-inf"), "very difficult"),
    ],
}

LANG_FORMULAS = {
    "en": ["flesch_reading_ease"],
    "fr": ["kandel_moles"],
    "es": ["fernandez_huerta", "szigriszt_pazos"],
}
FUNCS = {
    "flesch_reading_ease": flesch_reading_ease,
    "kandel_moles": kandel_moles,
    "fernandez_huerta": fernandez_huerta,
    "szigriszt_pazos": szigriszt_pazos,
}


def band(name: str, score: float) -> str:
    for low, label in BANDS[name]:
        if score >= low:
            return label
    return "very difficult"
