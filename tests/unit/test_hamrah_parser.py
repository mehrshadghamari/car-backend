import json
import re
from pathlib import Path

SAMPLE_HTML = Path(__file__).resolve().parents[2] / "hamrah-mechanic-sample-html.html"


def test_parse_hamrah_next_data_prices():
    html = SAMPLE_HTML.read_text(encoding="utf-8")
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', html, re.DOTALL)
    assert match
    data = json.loads(match.group(1))
    price = data["props"]["pageProps"]["price"]
    assert price["priceUp"] == 1981000000
    assert price["priceDown"] == 1828000000
