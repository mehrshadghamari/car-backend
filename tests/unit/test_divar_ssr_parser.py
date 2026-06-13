from pathlib import Path

from src.infrastructure.adapters.divar.ssr_parser import parse_search_page_from_html

SAMPLE_HTML = Path(__file__).resolve().parents[2] / "divar-sample-html-element.html"


def test_parse_divar_sample_html():
    html = SAMPLE_HTML.read_text(encoding="utf-8")
    page = parse_search_page_from_html(html)
    assert len(page.listings) >= 20
    first = page.listings[0]
    assert first.token
    assert first.price > 0
    assert first.title
