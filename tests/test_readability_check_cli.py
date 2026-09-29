import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from readability_check import cli
from readability_check.analyze import AnalysisError, Options, analyze_html

EASY = ("<html lang='en'><body><main>" + "<p>The cat sat on the mat. The dog ran to the man.</p>" * 4
        + "</main></body></html>")
HARD = ("<html lang='en'><body><main><p>The implementation of institutional organizational "
        "methodologies necessitates comprehensive interdepartmental communication throughout "
        "the multinational corporation, notwithstanding considerable administrative complexity "
        "and unprecedented technological transformation.</p></main></body></html>")
FR = ("<html lang='fr'><body><main><p>Le chat dort sur le canap\u00e9. Nous aimons notre maison.</p>"
      "</main></body></html>")
ES = ("<html lang='es-MX'><body><article><p>El gato duerme en la casa. Nosotros vivimos en la ciudad.</p>"
      "</article></body></html>")
PAGES = {"/easy": EASY, "/hard": HARD, "/fr": FR, "/es": ES,
         "/secret/page": EASY, "/nolang": "<html><body><p>Some words in a sentence here.</p></body></html>"}
ROBOTS = "User-agent: *\nAllow: /\nDisallow: /secret/\n"
hits = []


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        hits.append(self.path)
        if self.path == "/robots.txt":
            body, ctype, code = ROBOTS, "text/plain", 200
        elif self.path in PAGES:
            body, ctype, code = PAGES[self.path], "text/html; charset=utf-8", 200
        elif self.path == "/data.json":
            body, ctype, code = "{}", "application/json", 200
        else:
            body, ctype, code = "nope", "text/plain", 404
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def base():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def run(capsys, *argv):
    code = cli.main(["--delay", "0", *argv])
    return code, capsys.readouterr().out


def test_analyze_english_easy():
    r = analyze_html(EASY)
    assert r["lang"] == "en" and r["sentences"] == 8 and r["words"] == 4 * 6 + 4 * 6
    assert r["scores"]["flesch_reading_ease"]["value"] > 90
    assert r["grade"] < 2


def test_analyze_languages_and_override():
    assert analyze_html(FR)["primary_score"] == "kandel_moles"
    es = analyze_html(ES)
    assert set(es["scores"]) == {"fernandez_huerta", "szigriszt_pazos"} and es["grade"] is None
    assert analyze_html(FR, Options(lang="en"))["lang_source"] == "override"
    with pytest.raises(AnalysisError):
        analyze_html("<html><body><p>Some words in a sentence here.</p></body></html>")


def test_long_sentences_and_paragraphs():
    r = analyze_html(HARD, Options(long_sentence=20, long_paragraph=10))
    assert len(r["long_sentences"]) == 1 and len(r["long_paragraphs"]) == 1
    assert analyze_html(HARD)["long_sentences"] == []
    assert r["hardest_sentences"][0]["grade"] > 20


def test_local_file_markdown_and_output(tmp_path, capsys):
    f = tmp_path / "page.html"
    f.write_text(HARD, encoding="utf-8")
    out = tmp_path / "r.md"
    code = cli.main([str(f), "--output", str(out)])
    assert code == 0 and capsys.readouterr().out == ""
    text = out.read_text(encoding="utf-8")
    assert "# Readability report" in text and "Flesch Reading Ease" in text and "Hardest sentences" in text


def test_jargon_file(tmp_path, capsys):
    j = tmp_path / "j.txt"
    j.write_text("# mine\nimplementation\n", encoding="utf-8")
    f = tmp_path / "p.html"
    f.write_text(HARD, encoding="utf-8")
    code, out = run(capsys, str(f), "--jargon-file", str(j), "--format", "json")
    assert json.loads(out)["pages"][0]["jargon"] == {"implementation": 1}
    code, out = run(capsys, str(f), "--jargon-file", str(j), "--no-default-jargon", "--format", "json")
    assert json.loads(out)["pages"][0]["jargon"] == {"implementation": 1}


def test_threshold_exit_codes(tmp_path, capsys):
    easy = tmp_path / "e.html"
    easy.write_text(EASY, encoding="utf-8")
    hard = tmp_path / "h.html"
    hard.write_text(HARD, encoding="utf-8")
    assert run(capsys, str(easy), "--min-score", "60", "--max-grade", "8")[0] == 0
    code, out = run(capsys, str(hard), "--min-score", "60")
    assert code == 1 and "below --min-score" in out and "Thresholds: FAIL" in out
    assert run(capsys, str(hard), "--max-grade", "8")[0] == 1
    assert run(capsys, str(hard), "--long-sentence", "10", "--max-long-sentences", "0")[0] == 1
    assert run(capsys, str(hard), "--long-sentence", "10", "--max-long-sentences", "1")[0] == 0


def test_error_exit_codes(tmp_path, capsys):
    assert run(capsys)[0] == 2
    assert run(capsys, str(tmp_path / "missing.html"))[0] == 2
    empty = tmp_path / "empty.html"
    empty.write_text("<html lang='en'><body></body></html>", encoding="utf-8")
    assert run(capsys, str(empty))[0] == 2


def test_cli_on_local_server(base, capsys):
    hits.clear()
    code, out = run(capsys, base + "/easy", base + "/fr", base + "/es", "--format", "json")
    pages = json.loads(out)["pages"]
    assert code == 0
    assert [p["lang"] for p in pages] == ["en", "fr", "es"]
    assert hits.count("/robots.txt") == 1  # one robots.txt per host
    code, out = run(capsys, base + "/easy", base + "/hard", "--min-score", "60")
    assert code == 1 and "| Page |" in out


def test_robots_blocked_404_and_nonhtml(base, capsys):
    hits.clear()
    code, out = run(capsys, base + "/secret/page", "--format", "json")
    assert code == 2 and "blocked by robots.txt" in json.loads(out)["pages"][0]["error"]
    assert "/secret/page" not in hits
    code, out = run(capsys, base + "/missing", "--format", "json")
    assert code == 2 and "404" in json.loads(out)["pages"][0]["error"]
    code, out = run(capsys, base + "/data.json", "--format", "json")
    assert code == 2 and "not HTML" in json.loads(out)["pages"][0]["error"]
    code, out = run(capsys, base + "/nolang", "--format", "json")
    assert code == 2 and "lang" in json.loads(out)["pages"][0]["error"]
    code, out = run(capsys, base + "/nolang", "--lang", "en", "--format", "json")
    assert code == 0


def test_urls_file_and_max_pages(base, tmp_path, capsys):
    uf = tmp_path / "urls.txt"
    uf.write_text(f"# demo\n{base}/easy\n\n{base}/fr  # french\n", encoding="utf-8")
    code, out = run(capsys, "--urls-file", str(uf), "--format", "json")
    assert code == 0 and len(json.loads(out)["pages"]) == 2
    assert run(capsys, "--urls-file", str(uf), "--max-pages", "1")[0] == 2
