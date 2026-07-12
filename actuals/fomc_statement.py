"""FOMC声明文の本文を取得する。

event_masterのdatetime_jst（JST・声明発表時刻）から米東部時間の日付を逆算し、
https://www.federalreserve.gov/newsevents/pressreleases/monetary{YYYYMMDD}a.htm
のURLパターン（fetchers/fomc.pyで確認済みのFRB公式ページのリンク規則と同じ）から
声明ページを取得する。

ここで返すのは声明本文のテキストのみ。highlights欄（声明の変化／ドットチャート／
会見トーン等）への要約はAI（Claude）が本文を読んで作成する想定で、この関数の
役割は「その日の一次情報を機械的かつ正確に取ってくる」ところまでに絞っている。
"""
import datetime
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from fetchers.common import fetch_url
import requests

EASTERN = ZoneInfo("America/New_York")


def fetch_statement_text(datetime_jst_iso):
    dt_jst = datetime.datetime.fromisoformat(datetime_jst_iso)
    decision_date_et = dt_jst.astimezone(EASTERN).date()

    url = (
        "https://www.federalreserve.gov/newsevents/pressreleases/"
        f"monetary{decision_date_et.strftime('%Y%m%d')}a.htm"
    )
    try:
        resp = fetch_url(url)
    except requests.exceptions.HTTPError:
        return None, url

    soup = BeautifulSoup(resp.text, "html.parser")
    article = soup.find("div", id="article")
    if not article:
        return None, url
    return article.get_text("\n", strip=True), url


if __name__ == "__main__":
    import sys

    dt_iso = sys.argv[1] if len(sys.argv) > 1 else None
    if not dt_iso:
        print("usage: python -m actuals.fomc_statement <datetime_jst ISO8601>")
        raise SystemExit(1)
    text, url = fetch_statement_text(dt_iso)
    print("URL:", url)
    print("---")
    print(text)
