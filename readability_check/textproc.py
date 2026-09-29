"""Main-text extraction from HTML, paragraph and sentence splitting, word tokens."""
from __future__ import annotations

import re
from html.parser import HTMLParser

VOID = {"meta", "link", "img", "br", "hr", "input", "area", "base", "col", "embed",
        "source", "track", "wbr", "param"}
SKIP = {"script", "style", "noscript", "template", "svg", "iframe", "canvas", "head",
        "title", "nav", "header", "footer", "aside", "form", "button", "select",
        "textarea", "option", "dialog"}
SKIP_ROLES = {"navigation", "banner", "contentinfo", "complementary", "search"}
BLOCK = {"p", "div", "li", "ul", "ol", "section", "article", "main", "blockquote",
         "tr", "td", "th", "table", "h1", "h2", "h3", "h4", "h5", "h6", "dd", "dt",
         "dl", "figure", "figcaption", "pre", "hr", "details", "summary", "body",
         "tbody", "thead", "address"}
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class _Extractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool, bool, bool]] = []  # tag, skip, main, heading
        self.blocks: list[tuple[str, bool]] = []  # text, in_main
        self.lang: str | None = None
        self._buf: list[str] = []
        self._buf_main = False
        self._skip = 0
        self._main = 0
        self._heading = 0

    def _flush(self) -> None:
        text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
        if text:
            self.blocks.append((text, self._buf_main))
        self._buf = []
        self._buf_main = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html" and a.get("lang"):
            self.lang = a["lang"]
        if tag in BLOCK:
            self._flush()
        if tag in VOID:
            return
        skip = (tag in SKIP or (a.get("role") or "").lower() in SKIP_ROLES
                or "hidden" in a or (a.get("aria-hidden") or "").lower() == "true")
        main = tag in ("main", "article")
        heading = tag in HEADINGS
        self.stack.append((tag, skip, main, heading))
        self._skip += skip
        self._main += main
        self._heading += heading

    def handle_endtag(self, tag):
        if tag in BLOCK:
            self._flush()
        if tag in VOID:
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for _t, skip, main, heading in self.stack[i:]:
                    self._skip -= skip
                    self._main -= main
                    self._heading -= heading
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self._skip or self._heading:
            return
        self._buf.append(data)
        if self._main:
            self._buf_main = True

    def close(self):
        super().close()
        self._flush()


_TERMINAL = re.compile(r"[.!?\u2026][\"'\u201d\u00bb)\]]*$")


def extract(html: str) -> dict:
    """Return {"lang", "method", "paragraphs"}.

    Text inside <main>/<article> is used when there is any; otherwise all of the
    body except nav, header, footer, aside, script, style, forms and headings.
    Headings are left out (they are labels, not sentences), and so are very short
    blocks without end punctuation (menu items, button labels).
    """
    p = _Extractor()
    p.feed(html)
    p.close()
    blocks = [(t, m) for t, m in p.blocks if len(words(t)) >= 4 or _TERMINAL.search(t)]
    main_blocks = [t for t, m in blocks if m]
    if main_blocks:
        return {"lang": p.lang, "method": "main/article", "paragraphs": main_blocks}
    return {"lang": p.lang, "method": "body", "paragraphs": [t for t, _ in blocks]}


# ---------------------------------------------------------------- words

_WORD = re.compile(r"[^\W\d_]+(?:['\u2019\-][^\W\d_]+)*")


def words(text: str) -> list[str]:
    """Tokens that contain letters; pure numbers are not counted as words."""
    return _WORD.findall(text)


# ------------------------------------------------------------- sentences

ABBREVIATIONS = {
    "en": {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "inc", "ltd", "co",
           "no", "e.g", "i.e", "u.s", "u.k", "approx", "dept", "est", "fig", "mt", "gen"},
    "fr": {"m", "mme", "mmes", "mlle", "dr", "pr", "me", "st", "ste", "vs", "cf", "env",
           "p.ex", "n\u00b0", "e.g", "i.e", "av", "bd", "fig", "tel", "t\u00e9l", "min",
           "max", "ex", "resp"},
    "es": {"sr", "sra", "srta", "dr", "dra", "prof", "ud", "uds", "vs", "etc", "p.ej",
           "e.g", "i.e", "av", "avda", "pag", "p\u00e1g", "tel", "ee.uu", "no", "n\u00ba",
           "art", "cf", "fig"},
}
_BOUNDARY = re.compile(r"([.!?\u2026]+)([\"'\u201d\u00bb)\]]*)\s+")
_OPENERS = "\u00bf\u00a1\"'\u201c\u00ab(["


def split_sentences(text: str, lang: str = "en") -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    abbr = ABBREVIATIONS.get(lang, ABBREVIATIONS["en"])
    out: list[str] = []
    start = 0
    for m in _BOUNDARY.finditer(text):
        nxt = text[m.end():m.end() + 1]
        if not nxt or not (nxt.isupper() or nxt.isdigit() or nxt in _OPENERS):
            continue
        if m.group(1) == ".":
            tokens = text[start:m.start()].split()
            last = tokens[-1].lstrip("\"'\u201c\u00ab([").lower() if tokens else ""
            if last in abbr or re.fullmatch(r"[^\W\d_]", last) \
                    or re.fullmatch(r"(?:[^\W\d_]\.)+[^\W\d_]", last):
                continue
        out.append(text[start:m.end()].strip())
        start = m.end()
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return [s for s in out if words(s)]
