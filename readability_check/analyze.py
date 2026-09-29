"""Analyse one HTML document and return a plain dict (JSON-ready)."""
from __future__ import annotations

from dataclasses import dataclass, field

from . import formulas
from .checks import DEFAULT_JARGON, jargon_hits, passive_hints
from .syllables import count_syllables
from .textproc import extract, split_sentences, words

SUPPORTED = ("en", "fr", "es")


class AnalysisError(Exception):
    pass


@dataclass
class Options:
    lang: str | None = None
    long_sentence: int = 25
    long_paragraph: int = 150
    jargon: list[str] = field(default_factory=list)  # extra terms
    default_jargon: bool = True
    top: int = 5


def detect_lang(html_lang: str | None, override: str | None) -> tuple[str, str]:
    if override:
        code = override.lower()[:2]
        if code not in SUPPORTED:
            raise AnalysisError(f"unsupported language '{override}' (use en, fr or es)")
        return code, "override"
    if not html_lang:
        raise AnalysisError("no <html lang> found; pass --lang en|fr|es")
    code = html_lang.strip().lower().replace("_", "-")[:2]
    if code not in SUPPORTED:
        raise AnalysisError(f"unsupported html lang '{html_lang}' (use --lang en|fr|es)")
    return code, "html lang"


def analyze_html(html: str, opts: Options | None = None) -> dict:
    opts = opts or Options()
    ex = extract(html)
    lang, lang_source = detect_lang(ex["lang"], opts.lang)

    sentences: list[dict] = []
    long_paragraphs = []
    n_words = n_syll = 0
    for para in ex["paragraphs"]:
        pw = len(words(para))
        if pw > opts.long_paragraph:
            long_paragraphs.append({"words": pw, "text": para})
        for s in split_sentences(para, lang):
            toks = words(s)
            syl = sum(count_syllables(t, lang) for t in toks)
            sentences.append({"text": s, "words": len(toks), "syllables": syl})
            n_words += len(toks)
            n_syll += syl
    if not sentences:
        raise AnalysisError("no readable text found")

    n_sent = len(sentences)
    scores = {}
    for name in formulas.LANG_FORMULAS[lang]:
        value = formulas.FUNCS[name](n_words, n_sent, n_syll)
        scores[name] = {"value": round(value, 1), "band": formulas.band(name, value)}
    grade = None
    if lang == "en":
        grade = round(formulas.flesch_kincaid_grade(n_words, n_sent, n_syll), 1)

    long_sentences = [s for s in sentences if s["words"] > opts.long_sentence]
    hardest = sorted(
        (dict(s, grade=round(formulas.sentence_grade(s["words"], s["syllables"]), 1),
              syllables_per_word=round(s["syllables"] / s["words"], 2)) for s in sentences),
        key=lambda s: -s["grade"])[:opts.top]

    passive = None
    if lang == "en":
        passive = []
        for s in sentences:
            phrase = passive_hints(s["text"])
            if phrase:
                passive.append({"phrase": phrase, "text": s["text"]})

    terms = (DEFAULT_JARGON[lang] if opts.default_jargon else []) + list(opts.jargon)
    hits = jargon_hits(" ".join(ex["paragraphs"]), terms)

    return {
        "lang": lang,
        "lang_source": lang_source,
        "method": ex["method"],
        "paragraphs": len(ex["paragraphs"]),
        "sentences": n_sent,
        "words": n_words,
        "syllables": n_syll,
        "words_per_sentence": round(n_words / n_sent, 1),
        "syllables_per_word": round(n_syll / n_words, 2),
        "primary_score": formulas.PRIMARY[lang],
        "scores": scores,
        "grade": grade,
        "long_sentence_limit": opts.long_sentence,
        "long_sentences": long_sentences,
        "long_paragraph_limit": opts.long_paragraph,
        "long_paragraphs": long_paragraphs,
        "passive_hints": passive,
        "jargon": hits,
        "hardest_sentences": hardest,
    }
