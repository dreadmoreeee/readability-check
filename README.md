# readability-check

Readability scores for **web pages in English, French and Spanish**, with the sentences that cause them. It takes the main text of a page (not the menu or the footer), scores it with the published formula for its language, and can fail a CI job when a page gets too hard to read.

```
python -m readability_check https://example.com/ page.html --min-score 60 --max-grade 9
```

- **The right formula per language**, each cited in the code:
  - EN: Flesch Reading Ease (Flesch 1948) and Flesch-Kincaid grade level (Kincaid et al. 1975).
  - FR: Kandel & Moles (1958): `207 - 1.015*(words/sentences) - 73.6*(syllables/words)`.
  - ES: Fernandez Huerta (1959): `206.84 - 0.60*(syllables per 100 words) - 1.02*(sentences per 100 words)`, and Szigriszt-Pazos perspicuity (1993): `206.835 - 62.3*(syllables/words) - (words/sentences)`.
  - Each score comes with an interpretation band ("plain language", "fairly difficult", ...).
- **Main text only.** Uses `<main>`/`<article>` when present, otherwise the body without nav, header, footer, aside, script, style, forms and headings. The language comes from `<html lang>` (or `--lang`).
- **Rule-based syllable counters** for each language (silent-e and `-le` in English, mute final `e/es/ent` in French, diphthong/hiatus with accented `i`/`u` in Spanish), tested on known words. No dictionaries, no dependencies.
- **Sentence splitter** that knows common abbreviations (`Dr.`, `Sr.`, `M.`, `e.g.`, initials, decimals).
- **What to fix**: long sentences (> 25 words) and long paragraphs (> 150 words), both configurable; English passive-voice hints (a form of "to be" plus a past participle, labelled as hints); jargon from a small default list per language plus `--jargon-file`; the 5 hardest sentences of each page.
- **CI-ready**: `--min-score`, `--max-grade`, `--max-long-sentences`. Exit 0 ok, 1 a threshold failed, 2 error (page not found, blocked by robots.txt, no text, no language).
- **Polite**: GET only, `robots.txt` read with a copy of the RFC 9309 matcher from [robots9309](https://github.com/dreadmoreeee/robots9309) (`--no-robots` turns it off), at least `--delay 1` second between requests, at most `--max-pages 30` URLs per run. It never submits a form or logs in.

## Measured result

Run against my own sites (four required pages plus two more, 6 page loads, 1 s apart, robots.txt respected), with `--min-score 60 --max-grade 8`. The table is the start of the real output; the full report is in [examples/sample-report.md](examples/sample-report.md).

```
$ python -m readability_check https://demarkstudio.ca/en/ https://marvin.demarkstudio.ca/ https://demarkstudio.ca/fr/conception-web/miramichi https://marvin.demarkstudio.ca/es/ https://demarkstudio.ca/en/pricing https://demarkstudio.ca/fr/ --jargon-file examples/jargon.txt --min-score 60 --max-grade 8
| Page | Lang | Score | Reading | Grade | Sentences | Long | Status |
|---|---|---|---|---|---|---|---|
| https://demarkstudio.ca/en/ | en | 64.3 | plain language | 7.4 | 144 | 19 | ok |
| https://marvin.demarkstudio.ca/ | en | 54.1 | fairly difficult | 9.0 | 142 | 31 | FAIL |
| https://demarkstudio.ca/fr/conception-web/miramichi | fr | 74.4 | fairly easy |  | 32 | 4 | ok |
| https://marvin.demarkstudio.ca/es/ | es | 77.1 | fairly easy |  | 144 | 35 | ok |
| https://demarkstudio.ca/en/pricing | en | 63.9 | plain language | 6.8 | 107 | 1 | ok |
| https://demarkstudio.ca/fr/ | en | 64.3 | plain language | 7.4 | 144 | 19 | ok |
(exit code 1)
```

Spanish page, from the same report (trimmed):

```
## https://marvin.demarkstudio.ca/es/
- Language: es (html lang)
- Text taken from: main/article; 120 paragraphs, 144 sentences, 2105 words, 4306 syllables
- Averages: 14.6 words per sentence, 2.05 syllables per word

| Formula | Score | Reading |
| Fernandez Huerta (1959) (primary) | 77.1 | fairly easy |
| Szigriszt-Pazos (1993) | 64.8 | normal |

**Long sentences** (> 25 words): 35
**Hardest sentences** (top 5, by sentence grade from words and syllables per word)
1. grade 26.9, 39 words, 2.31 syll/word: Lista cada script que ejecuta una pagina, incluidos los que se anaden en tiempo de ejecucion: ...
```

```
$ python -m pytest -q -p no:cacheprovider --import-mode=importlib readability-check
72 passed in 0.82s
```

What I read from it, honestly:

- The two English pages land around "plain language" (64) and "fairly difficult" (54). The portfolio page fails the grade limit of 8 (it is 9.0) because it describes projects in long, colon-heavy lines ("For gyms and personal trainers: huge bold type on ...").
- `https://demarkstudio.ca/fr/` returned the same English text as `/en/` (identical counts, `html lang` is `en`), so that row is not a French measurement. The French score comes from the `conception-web/miramichi` page only.
- Most "long sentences" are not sentences: they are template descriptions, lists and captions written as one line without a full stop. The tool cannot tell them from prose, and neither can the formulas.
- The default jargon lists found nothing on these pages.

## Limits of the formulas

These formulas were fitted on continuous prose in the 1940s to 1990s. They only see word length and sentence length, so they know nothing about vocabulary, layout, headings, or whether the reader wants the information. A web page made of short list items and one-line descriptions can score "easy" while being hard to use, and the reverse. Use the score to compare versions of the same page and to find the worst sentences, not as a verdict. Syllable counting by rules is a few percent off (loan words, acronyms and product names such as `hreflang` are guessed), which moves a score by a point or two. Numbers are not counted as words; headings and very short lines without end punctuation (menu items, buttons) are left out. The French and Spanish scales are read like Flesch's; the Kandel-Moles bands below are the usual adaptation, not a table from the original paper. The passive-voice check only exists for English and is a hint: it misses many passives and flags adjectives like "is tired".

## Interpretation bands

| Score | Flesch (EN) / Kandel-Moles (FR) / Fernandez Huerta (ES) | Szigriszt-Pazos (ES, INFLESZ) |
|---|---|---|
| 90 and up | very easy | very easy (80 and up) |
| 80-90 | easy | very easy |
| 70-80 | fairly easy | fairly easy (65-80) |
| 60-70 | plain language (ES: normal) | fairly easy (65-80) / normal (55-65) |
| 50-60 | fairly difficult | normal (55-65) / somewhat difficult (40-55) |
| 30-50 | difficult | somewhat difficult (40-55) / very difficult (below 40) |
| below 30 | very difficult | very difficult |

The grade level (English only) is a US school grade: 8 means an eighth grader can follow it.

## CLI

```
python -m readability_check [URL|file ...] [--urls-file urls.txt] [--lang en|fr|es]
       [--format markdown|json] [--output report.md]
       [--long-sentence 25] [--long-paragraph 150]
       [--jargon-file examples/jargon.txt] [--no-default-jargon]
       [--min-score N] [--max-grade N] [--max-long-sentences N]
       [--delay 1] [--timeout 15] [--max-pages 30] [--no-robots]
```

`--min-score` applies to the primary score of the page language (Flesch, Kandel-Moles, Fernandez Huerta). `--max-grade` only applies to English pages. A jargon file has one term per line, `#` for comments; matching ignores case and accents. `pip install .` also installs a `readability-check` command. [examples/jargon.txt](examples/jargon.txt) is a sample list.

## Author

Marvin Palencia, founder of [DeMark Studio](https://demarkstudio.ca), Miramichi, New Brunswick, Canada. Portfolio: [marvin.demarkstudio.ca](https://marvin.demarkstudio.ca)

MIT License.
