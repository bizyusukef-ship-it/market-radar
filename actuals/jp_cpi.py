"""総務省統計局「消費者物価指数(CPI) 全国（最新の月次結果の概要）」ページから
全国CPI（コア＝生鮮食品を除く総合、前年同月比）の実績値を取得する。

https://www.stat.go.jp/data/cpi/sokuhou/tsuki/index-z.html
（2026-07-09時点で実ページを確認済み。常に「最新月」の結果のみを表示するページのため、
 発表当日近辺に実行する前提。過去分の再取得はできない）

このページには前回月の値が載っていないため、prior（前回値）は
actuals/history_store.py に蓄積した過去の自己記録から補う。
"""
import re

from bs4 import BeautifulSoup

from fetchers.common import fetch_url
from . import history_store

URL = "https://www.stat.go.jp/data/cpi/sokuhou/tsuki/index-z.html"
EVENT_KEY = "jp_cpi"
UNIT = "%"

CORE_RE = re.compile(r"生鮮食品を除く総合指数.*?前年同月比は([\d.]+)％の(上昇|下落|低下)")


def fetch_jp_cpi_actual(as_of_date):
    """戻り値: (actual_str_or_None, prior_str_or_None, unit_str)"""
    resp = fetch_url(URL)
    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(" ", strip=True)

    m = CORE_RE.search(text)
    if not m:
        return None, history_store.get_prior(EVENT_KEY, as_of_date.isoformat()), UNIT

    value, direction = m.groups()
    actual = value if direction == "上昇" else f"-{value}"

    prior = history_store.get_prior(EVENT_KEY, as_of_date.isoformat())
    history_store.record(EVENT_KEY, as_of_date.isoformat(), actual)

    return actual, prior, UNIT


if __name__ == "__main__":
    import sys
    import datetime

    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    d = datetime.date.fromisoformat(date_str)
    actual, prior, unit = fetch_jp_cpi_actual(d)
    print(f"jp_cpi: actual={actual}{unit} prior={prior}{unit}")
