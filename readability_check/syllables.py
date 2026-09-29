"""Rule-based syllable counters for English, French and Spanish.

These are heuristics, not dictionaries: expect an error of a few percent on
running text, which moves a reading-ease score by roughly a point or two.
"""
from __future__ import annotations

import re

_SPLIT = re.compile("['\u2019\\-]")


def _parts(word: str) -> list[str]:
    return [p for p in _SPLIT.split(word.lower()) if p]


# ---------------------------------------------------------------- English

_EN_EXCEPTIONS = {
    "people": 2, "area": 3, "idea": 3, "create": 2, "created": 3, "creating": 3,
    "creative": 3, "being": 2, "science": 2, "business": 2, "every": 2,
    "different": 3, "evening": 2, "usually": 4, "video": 3, "radio": 3,
    "quiet": 2, "poem": 2, "lion": 2, "orange": 2, "beautiful": 3,
    "through": 1, "once": 1, "one": 1, "queue": 1, "the": 1, "were": 1,
    "here": 1, "there": 1, "where": 1, "are": 1, "our": 1, "hour": 1,
    "fire": 1, "wire": 1, "tired": 1, "desire": 2, "real": 1, "really": 2,
    "already": 3, "experience": 4, "society": 4, "variety": 4, "website": 2,
    "email": 2, "user": 2, "users": 2, "cafe": 2, "recipe": 3, "simile": 3,
    "maybe": 2, "everyone": 3, "someone": 2, "anyone": 3, "service": 2,
    "minute": 2, "chocolate": 3, "vegetable": 4, "interesting": 3,
    "comfortable": 3, "family": 3, "camera": 3, "average": 3, "several": 3,
    "generally": 4, "literally": 4, "actually": 4, "totally": 3,
}


def count_en(word: str) -> int:
    total = sum(_en_part(p) for p in _parts(word))
    return max(1, total)


def _en_part(w: str) -> int:
    w = re.sub(r"[^a-z]", "", w)
    if not w:
        return 0
    if w in _EN_EXCEPTIONS:
        return _EN_EXCEPTIONS[w]
    n = len(re.findall(r"[aeiouy]+", w))
    if n == 0:
        return 0
    # -ia, -io inside a word are usually two sounds (radio, media, violin)
    n += len(re.findall(r"[^tcsgxl]ia|[^tcsgxl]io(?!n)|uo|ua(?!r)|eo(?!u)", w[1:]))
    if n > 1:
        # silent final e, but not -le after a consonant (table, little)
        if w.endswith("e") and not re.search(r"[^aeiouy]le$", w):
            n -= 1
        elif w.endswith("es") and not re.search(r"(?:[sxz]|ch|sh|c|g)es$", w) \
                and not re.search(r"[^aeiouy]les$", w):
            n -= 1
        elif w.endswith("ed") and not re.search(r"[td]ed$", w):
            n -= 1
    return max(1, n)


# ----------------------------------------------------------------- French

_FR_VOWELS = "aeiouy\u00e0\u00e2\u00e4\u00e9\u00e8\u00ea\u00eb\u00ee\u00ef\u00f4\u00f6\u00f9\u00fb\u00fc\u0153\u00e6"
_FR_DIAERESIS = "\u00e4\u00eb\u00ef\u00f6\u00fc"
_FR_NON_MUTE_ENT = {
    "souvent", "comment", "moment", "argent", "client", "patient", "pr\u00e9sent",
    "diff\u00e9rent", "excellent", "urgent", "r\u00e9cent", "cent", "vent", "dent",
    "parent", "content", "lent", "talent", "agent", "serpent", "accident",
    "incident", "r\u00e9sident", "pr\u00e9sident", "cependant", "pourtant",
}
_FR_KEEP_E = re.compile(r"[bcdfgptv][lr]es?$")


def count_fr(word: str) -> int:
    total = sum(_fr_part(p) for p in _parts(word))
    return max(1, total)


def _fr_part(w: str) -> int:
    w = re.sub("[^a-z" + _FR_VOWELS + "]", "", w)
    if not w:
        return 0
    n = 0
    prev_vowel = False
    prev = ""
    for ch in w:
        if ch in _FR_VOWELS:
            # a diaeresis opens a new syllable (naif, noel); so does a vowel after e-acute (cre-a-tion)
            if not prev_vowel or ch in _FR_DIAERESIS or (prev in "\u00e9\u00e8\u00ea" and ch != "e"):
                n += 1
            prev_vowel = True
        else:
            prev_vowel = False
        prev = ch
    if n == 0:
        return 0
    if n > 1:
        if w.endswith("ent") and len(w) > 4 and w not in _FR_NON_MUTE_ENT \
                and not w.endswith("ment") and w[-4] not in _FR_VOWELS:
            n -= 1  # 3rd person plural verb ending: parlent
        elif w.endswith("es") and len(w) > 2 and w[-3] not in _FR_VOWELS \
                and not _FR_KEEP_E.search(w):
            n -= 1
        elif w.endswith("e") and len(w) > 1 and w[-2] not in _FR_VOWELS \
                and not _FR_KEEP_E.search(w):
            n -= 1
    return max(1, n)


# ---------------------------------------------------------------- Spanish

_ES_STRONG = set("aeo\u00e1\u00e9\u00f3\u00ed\u00fa")  # accented i/u act as strong
_ES_WEAK = set("iu\u00fc")
_ES_VOWELS = _ES_STRONG | _ES_WEAK


def count_es(word: str) -> int:
    total = sum(_es_part(p) for p in _parts(word))
    return max(1, total)


def _es_part(w: str) -> int:
    w = re.sub("[^a-z\u00e1\u00e9\u00ed\u00f3\u00fa\u00fc\u00f1]", "", w)
    if not w:
        return 0
    # u is silent in que/qui/gue/gui
    w = re.sub("(?<=[qg])u(?=[ei\u00e9\u00ed])", "x", w)
    n = 0
    i = 0
    while i < len(w):
        if w[i] not in _ES_VOWELS:
            i += 1
            continue
        j = i
        while j < len(w) and w[j] in _ES_VOWELS:
            j += 1
        run = w[i:j]
        n += 1
        # hiatus: two adjacent strong vowels (accented i/u count as strong) split the run
        n += sum(1 for a, b in zip(run, run[1:]) if a in _ES_STRONG and b in _ES_STRONG)
        i = j
    return n


COUNTERS = {"en": count_en, "fr": count_fr, "es": count_es}


def count_syllables(word: str, lang: str) -> int:
    return COUNTERS[lang](word)
