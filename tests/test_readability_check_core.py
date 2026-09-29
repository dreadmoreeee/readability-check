import pytest

from readability_check import formulas
from readability_check.checks import jargon_hits, passive_hints
from readability_check.syllables import count_en, count_es, count_fr
from readability_check.textproc import extract, split_sentences, words


@pytest.mark.parametrize("word,n", [
    ("cat", 1), ("make", 1), ("table", 2), ("little", 2), ("the", 1), ("people", 2),
    ("beautiful", 3), ("created", 3), ("wanted", 2), ("jumped", 1), ("boxes", 2),
    ("readability", 5), ("don't", 1), ("e-mail", 2), ("radio", 3), ("nation", 2),
    ("website", 2), ("simple", 2), ("business", 2),
])
def test_syllables_en(word, n):
    assert count_en(word) == n


@pytest.mark.parametrize("word,n", [
    ("chat", 1), ("table", 2), ("maison", 2), ("parle", 1), ("parlent", 1),
    ("belles", 1), ("livre", 2), ("idee", 2), ("id\u00e9e", 2), ("na\u00efve", 2),
    ("beaucoup", 2), ("souvent", 2), ("gouvernement", 4), ("l'\u00e9cole", 2),
    ("cr\u00e9ation", 3), ("a", 1),
])
def test_syllables_fr(word, n):
    assert count_fr(word) == n


@pytest.mark.parametrize("word,n", [
    ("casa", 2), ("queso", 2), ("guitarra", 3), ("ping\u00fcino", 3),
    ("pa\u00eds", 2), ("canci\u00f3n", 2), ("d\u00eda", 2),
    ("re\u00edr", 2), ("ciudad", 2), ("a\u00e9reo", 4), ("aire", 2), ("Mar\u00eda", 3),
    ("h\u00e9roe", 3), ("cuidado", 3), ("web", 1),
])
def test_syllables_es(word, n):
    assert count_es(word) == n


def test_es_accented_weak_vowel_breaks_diphthong():
    assert count_es("rio") == 1 and count_es("r\u00edo") == 2
    assert count_es("ciudad") == 2  # weak+weak stays one syllable
    assert count_es("pa\u00eds") == 2 and count_es("pais") == 1
    assert count_es("mi\u00fa") == 1 and count_es("ba\u00fal") == 2 and count_es("miau") == 1


def test_formulas_hand_computed():
    # "The cat sat on the mat." -> 6 words, 1 sentence, 6 syllables
    assert formulas.flesch_reading_ease(6, 1, 6) == pytest.approx(116.145)
    assert formulas.flesch_kincaid_grade(6, 1, 6) == pytest.approx(-1.45)
    assert formulas.kandel_moles(6, 1, 6) == pytest.approx(127.31)
    assert formulas.fernandez_huerta(6, 1, 6) == pytest.approx(206.84 - 60 - 1.02 * 100 / 6)
    assert formulas.szigriszt_pazos(6, 1, 6) == pytest.approx(138.535)
    # 100 words, 5 sentences, 150 syllables
    assert formulas.flesch_reading_ease(100, 5, 150) == pytest.approx(206.835 - 20.3 - 126.9)
    assert formulas.fernandez_huerta(100, 5, 150) == pytest.approx(206.84 - 90 - 5.1)


def test_bands():
    assert formulas.band("flesch_reading_ease", 95) == "very easy"
    assert formulas.band("flesch_reading_ease", 65) == "plain language"
    assert formulas.band("flesch_reading_ease", 10) == "very difficult"
    assert formulas.band("szigriszt_pazos", 60) == "normal"
    assert formulas.band("fernandez_huerta", 85) == "easy"


def test_sentence_split_basic():
    s = split_sentences("It works. Does it? Yes! Really.", "en")
    assert s == ["It works.", "Does it?", "Yes!", "Really."]


def test_sentence_split_abbreviations():
    s = split_sentences("Dr. Smith met Mr. Jones at 5 p.m. today. They spoke about U.S. law, e.g. Tax. "
                        "It cost 3.50 dollars. Done.", "en")
    assert len(s) == 4, s
    assert s[0].startswith("Dr. Smith") and s[0].endswith("today.")
    assert split_sentences("M. Dupont est arriv\u00e9. Il parle.", "fr") == ["M. Dupont est arriv\u00e9.", "Il parle."]
    assert len(split_sentences("El Sr. L\u00f3pez lleg\u00f3. \u00bfC\u00f3mo est\u00e1? Bien.", "es")) == 3


def test_sentence_split_initials_and_lowercase():
    assert len(split_sentences("J. K. Rowling wrote it. Then she slept.", "en")) == 2
    assert len(split_sentences("Version 2. beta is out. Next.", "en")) == 2


def test_words_ignore_numbers():
    assert words("In 2026, we sold 300 items (well-known).") == ["In", "we", "sold", "items", "well-known"]


HTML = """<html lang="en"><head><title>T</title><style>p{}</style></head><body>
<header><p>Site header text that should not count at all here.</p></header>
<nav><ul><li>Home</li><li>About us and other things to read</li></ul></nav>
<main><h1>Heading is skipped</h1>
<p>The first paragraph has two sentences. It is short.</p>
<aside><p>Related links that live inside an aside element only.</p></aside>
<p>Second paragraph with a <a href="#">link</a> inside it.</p>
<form><p>Please enter your details into this form now.</p></form>
<script>var x = "code code code code code";</script></main>
<footer><p>Copyright text in the footer that should be ignored.</p></footer></body></html>"""


def test_extract_main_skips_nav_footer():
    ex = extract(HTML)
    assert ex["lang"] == "en" and ex["method"] == "main/article"
    assert ex["paragraphs"] == ["The first paragraph has two sentences. It is short.",
                                "Second paragraph with a link inside it."]


def test_extract_body_fallback():
    html = ("<html lang='fr'><body><nav><p>Menu principal du site web ici.</p></nav>"
            "<div>Bonjour tout le monde. Ceci est un test.</div>"
            "<p>Acheter</p><footer>Pied de page du site web ici.</footer>"
            "<script>x</script></body></html>")
    ex = extract(html)
    assert ex["method"] == "body" and ex["lang"] == "fr"
    assert ex["paragraphs"] == ["Bonjour tout le monde. Ceci est un test."]


def test_extract_unclosed_and_role():
    html = ("<html><body><div role='navigation'><p>Skip me please this is navigation.</p></div>"
            "<p>One paragraph left open here.<p>Another one follows right after it.</body></html>")
    assert extract(html)["paragraphs"] == ["One paragraph left open here.", "Another one follows right after it."]


def test_passive_hints():
    assert passive_hints("The report was written by the team.") == "was written"
    assert passive_hints("The bug has been quickly fixed.") == "been quickly fixed"
    assert passive_hints("Mistakes were not corrected.") == "were not corrected"
    assert passive_hints("The code is really tested daily.") == "is really tested"
    assert passive_hints("The team wrote the report.") is None
    assert passive_hints("We need a hundred seeds.") is None
    assert passive_hints("It is being built now.") == "being built"


def test_jargon():
    hits = jargon_hits("We leverage synergy. Synergies are not synergy. Cle en main!",
                       ["synergy", "leverage", "cl\u00e9 en main", "turnkey"])
    assert hits == {"synergy": 2, "leverage": 1, "cl\u00e9 en main": 1}
    assert jargon_hits("Solutions-oriented and preleverage", ["solutions", "leverage"]) == {"solutions": 1}
