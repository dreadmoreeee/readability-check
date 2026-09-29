"""Style hints: English passive voice and jargon."""
from __future__ import annotations

import re
import unicodedata

from .textproc import words

_BE = {"am", "is", "are", "was", "were", "be", "been", "being"}
_ADVERB_OK = {"not", "never", "also", "often", "always", "still", "just", "then"}
_IRREGULAR = {
    "done", "made", "given", "taken", "shown", "written", "seen", "known", "built",
    "sent", "held", "found", "brought", "bought", "paid", "told", "sold", "kept",
    "left", "lost", "begun", "chosen", "driven", "eaten", "fallen", "forgotten",
    "gotten", "grown", "hidden", "thrown", "worn", "won", "understood", "spoken",
    "broken", "stolen", "drawn", "led", "met", "heard", "held", "born",
}
_NOT_PARTICIPLE = {"hundred", "sacred", "naked", "wicked", "indeed", "proceed", "succeed"}


def _is_participle(w: str) -> bool:
    if w in _IRREGULAR:
        return True
    return (w.endswith("ed") and len(w) >= 5 and not w.endswith("eed")
            and w not in _NOT_PARTICIPLE)


def passive_hints(sentence: str) -> str | None:
    """Return the matched phrase if the sentence looks passive, else None.

    Heuristic: a form of "to be", optionally followed by an adverb, followed by a
    word that looks like a past participle. It misses many passives and flags some
    adjectives ("is tired"), so treat results as hints.
    """
    toks = [t.lower().replace("\u2019", "'") for t in words(sentence)]
    for i, t in enumerate(toks):
        if t not in _BE:
            continue
        j = i + 1
        if j < len(toks) and (toks[j].endswith("ly") or toks[j] in _ADVERB_OK):
            j += 1
        if j < len(toks) and _is_participle(toks[j]):
            return " ".join(toks[i:j + 1])
    return None


DEFAULT_JARGON = {
    "en": ["leverage", "synergy", "utilize", "paradigm", "robust", "seamless", "holistic",
           "cutting-edge", "best-in-class", "end-to-end", "turnkey", "scalable",
           "stakeholder", "deliverable", "bandwidth", "ecosystem", "streamline",
           "empower", "state-of-the-art", "world-class", "solutions"],
    "fr": ["synergie", "levier", "de pointe", "cle en main", "holistique", "optimiser",
           "parties prenantes", "livrable", "ecosysteme", "forte valeur ajoutee",
           "innovant", "solutions", "performant", "scalable", "accompagnement"],
    "es": ["sinergia", "llave en mano", "holistico", "de vanguardia", "valor agregado",
           "ecosistema", "escalable", "proactivo", "empoderar", "optimizar",
           "soluciones integrales", "partes interesadas", "entregable"],
}


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


def load_jargon_file(path: str) -> list[str]:
    terms = []
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if line:
                terms.append(line)
    return terms


def jargon_hits(text: str, terms: list[str]) -> dict[str, int]:
    """Count whole-word/phrase matches, ignoring case and accents."""
    hay = strip_accents(text).lower()
    hits: dict[str, int] = {}
    for term in terms:
        norm = strip_accents(term).lower().strip()
        if not norm:
            continue
        pat = r"(?<![^\W_])" + r"\s+".join(re.escape(p) for p in norm.split()) + r"(?![^\W_])"
        n = len(re.findall(pat, hay))
        if n:
            hits[term] = hits.get(term, 0) + n
    return hits
