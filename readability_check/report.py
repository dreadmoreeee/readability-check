"""Markdown and JSON rendering."""
from __future__ import annotations

import json

LABELS = {
    "flesch_reading_ease": "Flesch Reading Ease (1948)",
    "kandel_moles": "Kandel & Moles (1958)",
    "fernandez_huerta": "Fernandez Huerta (1959)",
    "szigriszt_pazos": "Szigriszt-Pazos (1993)",
}
LIMIT = 200


def _clip(text: str, limit: int = LIMIT) -> str:
    text = text.replace("|", "\\|")
    return text if len(text) <= limit else text[:limit - 3].rstrip() + "..."


def to_json(pages: list[dict]) -> str:
    return json.dumps({"pages": pages}, indent=2, ensure_ascii=False) + "\n"


def to_markdown(pages: list[dict]) -> str:
    out = ["# Readability report", ""]
    ok = [p for p in pages if "error" not in p]
    if len(pages) > 1:
        out += ["| Page | Lang | Score | Reading | Grade | Sentences | Long | Status |",
                "|---|---|---|---|---|---|---|---|"]
        for p in pages:
            if "error" in p:
                out.append(f"| {p['source']} | | | | | | | ERROR: {p['error']} |")
                continue
            s = p["scores"][p["primary_score"]]
            grade = "" if p["grade"] is None else p["grade"]
            status = "FAIL" if p["failures"] else "ok"
            out.append(f"| {p['source']} | {p['lang']} | {s['value']} | {s['band']} | {grade} "
                       f"| {p['sentences']} | {len(p['long_sentences'])} | {status} |")
        out.append("")
    if not ok and len(pages) == 1:
        out += [f"## {pages[0]['source']}", "", f"Error: {pages[0]['error']}", ""]
    for p in pages:
        if "error" in p:
            if len(pages) > 1:
                out += [f"## {p['source']}", "", f"Error: {p['error']}", ""]
            continue
        out += [f"## {p['source']}", ""]
        out.append(f"- Language: {p['lang']} ({p['lang_source']})")
        out.append(f"- Text taken from: {p['method']}; {p['paragraphs']} paragraphs, "
                   f"{p['sentences']} sentences, {p['words']} words, {p['syllables']} syllables")
        out.append(f"- Averages: {p['words_per_sentence']} words per sentence, "
                   f"{p['syllables_per_word']} syllables per word")
        out += ["", "| Formula | Score | Reading |", "|---|---|---|"]
        for name, s in p["scores"].items():
            mark = " (primary)" if name == p["primary_score"] else ""
            out.append(f"| {LABELS[name]}{mark} | {s['value']} | {s['band']} |")
        if p["grade"] is not None:
            out.append(f"| Flesch-Kincaid grade (Kincaid et al. 1975) | {p['grade']} | US school grade |")
        out.append("")
        out.append(f"**Long sentences** (> {p['long_sentence_limit']} words): {len(p['long_sentences'])}")
        for s in p["long_sentences"][:10]:
            out.append(f"- ({s['words']} words) {_clip(s['text'])}")
        if len(p["long_sentences"]) > 10:
            out.append(f"- ... and {len(p['long_sentences']) - 10} more (see --format json)")
        out.append("")
        out.append(f"**Long paragraphs** (> {p['long_paragraph_limit']} words): {len(p['long_paragraphs'])}")
        for s in p["long_paragraphs"][:10]:
            out.append(f"- ({s['words']} words) {_clip(s['text'], 120)}")
        out.append("")
        if p["passive_hints"] is None:
            out.append("**Passive voice hints**: only checked for English.")
        else:
            out.append(f"**Passive voice hints** (heuristic, may be wrong): {len(p['passive_hints'])} of "
                       f"{p['sentences']} sentences")
            for h in p["passive_hints"][:10]:
                out.append(f"- \"{h['phrase']}\": {_clip(h['text'], 140)}")
            if len(p["passive_hints"]) > 10:
                out.append(f"- ... and {len(p['passive_hints']) - 10} more (see --format json)")
        out.append("")
        if p["jargon"]:
            terms = ", ".join(f"{t} x{n}" for t, n in sorted(p["jargon"].items(), key=lambda kv: -kv[1]))
            out.append(f"**Jargon**: {terms}")
        else:
            out.append("**Jargon**: none found")
        out += ["", f"**Hardest sentences** (top {len(p['hardest_sentences'])}, by sentence grade "
                    "from words and syllables per word)"]
        for i, s in enumerate(p["hardest_sentences"], 1):
            out.append(f"{i}. grade {s['grade']}, {s['words']} words, {s['syllables_per_word']} syll/word: "
                       f"{_clip(s['text'])}")
        out.append("")
        if p["failures"]:
            out.append("**Thresholds: FAIL**")
            out += [f"- {f}" for f in p["failures"]]
        elif p["thresholds"]:
            out.append("**Thresholds: ok**")
        out.append("")
    return "\n".join(out).rstrip() + "\n"
