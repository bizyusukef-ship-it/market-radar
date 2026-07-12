"""ESRI（内閣府経済社会総合研究所）「結果の概要」ページから、
最新のGDP速報（ポイント解説PDF）を辿って実質GDP成長率（年率）を取得する。

https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/gaiyou/gaiyou_top.html
（2026-07-09時点で実ページを確認済み。常に「最新の発表」を指すページのため、
 発表当日近辺に実行する前提）

このページのPDFには同じ四半期内の「1次→2次速報の改定幅」しか書かれておらず
前の四半期の値が載っていないため、prior（前回値）は history_store の自己記録から補う。
"""
import re

import pdfplumber
import io

from bs4 import BeautifulSoup

from fetchers.common import fetch_url
from . import history_store

GAIYOU_URL = "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/gaiyou/gaiyou_top.html"
EVENT_KEY = "jp_gdp"
UNIT = "%"

POINT_LINK_RE = re.compile(r"ポイント解説")
GDP_RATE_RE = re.compile(r"実質[▲\-]?[\d.]+％（年率([▲\-]?[\d.]+)％）")


def _find_point_pdf_url(soup, base_url="https://www.esri.cao.go.jp"):
    for a in soup.find_all("a"):
        if POINT_LINK_RE.search(a.get_text()):
            href = a.get("href")
            if href.startswith("http"):
                return href
            if href.startswith("/"):
                return base_url + href
            # 相対パス（../files/... 形式）
            return "https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/gaiyou/" + href
    return None


def fetch_jp_gdp_actual(as_of_date):
    """戻り値: (actual_str_or_None, prior_str_or_None, unit_str)"""
    resp = fetch_url(GAIYOU_URL)
    soup = BeautifulSoup(resp.text, "html.parser")

    pdf_url = _find_point_pdf_url(soup)
    if pdf_url is None:
        return None, history_store.get_prior(EVENT_KEY, as_of_date.isoformat()), UNIT

    pdf_resp = fetch_url(pdf_url)
    with pdfplumber.open(io.BytesIO(pdf_resp.content)) as pdf:
        text = pdf.pages[0].extract_text() or ""

    m = GDP_RATE_RE.search(text)
    if not m:
        return None, history_store.get_prior(EVENT_KEY, as_of_date.isoformat()), UNIT

    raw = m.group(1).replace("▲", "-")
    actual = raw

    prior = history_store.get_prior(EVENT_KEY, as_of_date.isoformat())
    history_store.record(EVENT_KEY, as_of_date.isoformat(), actual)

    return actual, prior, UNIT


if __name__ == "__main__":
    import sys
    import datetime

    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    d = datetime.date.fromisoformat(date_str)
    actual, prior, unit = fetch_jp_gdp_actual(d)
    print(f"jp_gdp: actual={actual}{unit} prior={prior}{unit}")
