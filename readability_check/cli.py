"""Command line interface. Exit codes: 0 ok, 1 threshold failed, 2 error."""
from __future__ import annotations

import argparse
import sys

from .analyze import AnalysisError, Options, analyze_html
from .checks import load_jargon_file
from .fetch import Fetcher, FetchError, read_file
from .report import to_json, to_markdown


def check_thresholds(page: dict, min_score, max_grade, max_long) -> tuple[list[str], list[str]]:
    """Return (thresholds that were set, failure messages)."""
    used, failures = [], []
    if min_score is not None:
        used.append("min-score")
        name = page["primary_score"]
        value = page["scores"][name]["value"]
        if value < min_score:
            failures.append(f"{name} {value} is below --min-score {min_score}")
    if max_grade is not None:
        used.append("max-grade")
        if page["grade"] is None:
            pass  # grade level is only defined for English
        elif page["grade"] > max_grade:
            failures.append(f"grade {page['grade']} is above --max-grade {max_grade}")
    if max_long is not None:
        used.append("max-long-sentences")
        n = len(page["long_sentences"])
        if n > max_long:
            failures.append(f"{n} long sentences (> {page['long_sentence_limit']} words) "
                            f"is above --max-long-sentences {max_long}")
    return used, failures


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="readability-check",
        description="Readability scores for web pages (en, fr, es). Exit 0 ok, 1 threshold failed, 2 error.")
    ap.add_argument("inputs", nargs="*", help="URLs (http/https) or local HTML files")
    ap.add_argument("--urls-file", help="file with one URL or path per line (# comments allowed)")
    ap.add_argument("--lang", choices=["en", "fr", "es"], help="override the <html lang> language")
    ap.add_argument("--format", choices=["markdown", "json"], default="markdown")
    ap.add_argument("--output", "-o", help="write the report to this file instead of stdout")
    ap.add_argument("--long-sentence", type=int, default=25, metavar="WORDS")
    ap.add_argument("--long-paragraph", type=int, default=150, metavar="WORDS")
    ap.add_argument("--jargon-file", help="extra jargon terms, one per line")
    ap.add_argument("--no-default-jargon", action="store_true", help="use only --jargon-file terms")
    ap.add_argument("--min-score", type=float, help="fail if the primary reading-ease score is lower")
    ap.add_argument("--max-grade", type=float, help="fail if the Flesch-Kincaid grade (English) is higher")
    ap.add_argument("--max-long-sentences", type=int, help="fail if a page has more long sentences")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests (default 1)")
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("--max-pages", type=int, default=30, help="most URLs to load in one run (default 30)")
    ap.add_argument("--no-robots", action="store_true", help="do not read robots.txt (not recommended)")
    return ap


def _is_url(s: str) -> bool:
    return s.lower().startswith(("http://", "https://"))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    inputs = list(args.inputs)
    try:
        if args.urls_file:
            with open(args.urls_file, encoding="utf-8-sig") as fh:
                inputs += [ln.split("#", 1)[0].strip() for ln in fh if ln.split("#", 1)[0].strip()]
        extra = load_jargon_file(args.jargon_file) if args.jargon_file else []
    except OSError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if not inputs:
        print("error: give at least one URL or HTML file", file=sys.stderr)
        return 2
    if sum(_is_url(i) for i in inputs) > args.max_pages:
        print(f"error: more than --max-pages ({args.max_pages}) URLs", file=sys.stderr)
        return 2

    opts = Options(lang=args.lang, long_sentence=args.long_sentence,
                   long_paragraph=args.long_paragraph, jargon=extra,
                   default_jargon=not args.no_default_jargon)
    fetcher = Fetcher(delay=args.delay, timeout=args.timeout, use_robots=not args.no_robots)
    pages, had_error, failed = [], False, False
    for src in inputs:
        try:
            html = fetcher.get(src) if _is_url(src) else read_file(src)
            page = analyze_html(html, opts)
            used, failures = check_thresholds(page, args.min_score, args.max_grade,
                                              args.max_long_sentences)
            page.update(thresholds=used, failures=failures)
            failed = failed or bool(failures)
        except (FetchError, AnalysisError) as e:
            page = {"error": str(e)}
            had_error = True
        pages.append({"source": src, **page})

    report = to_json(pages) if args.format == "json" else to_markdown(pages)
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(report)
        except OSError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(report)
    return 2 if had_error else (1 if failed else 0)
