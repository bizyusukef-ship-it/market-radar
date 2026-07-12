"""内閣府ESRIの「四半期別GDP速報 公表予定」ページをスクレイピングする。

ページ構造（2026-07-06時点で実ページを確認済み）:
  <h2><span id="a">四半期別GDP速報</span></h2>
  <table class="tableBase w_100">
    <tbody>
      <tr><td>2026年4-6月期（1次速報）</td><td>2026（令和8）年8月17日（月）</td><td>8時50分</td></tr>
      ...

市場インパクトが大きい「1次速報」のみを取り込み、2次速報は対象外とする。
"""
import datetime
import re

from bs4 import BeautifulSoup

from .common import fetch_url, jst_naive_to_iso, make_row
from config.impact_map import EVENT_DEFINITIONS

URL = "https://www.esri.cao.go.jp/jp/sna/kouhyou/kouhyou_top.html"

DATE_RE = re.compile(r"(\d{4}).*?年\s*(\d{1,2})月\s*(\d{1,2})日")
TIME_RE = re.compile(r"(\d{1,2})時\s*(\d{1,2})分")


def fetch_jp_gdp_events():
    resp = fetch_url(URL)
    soup = BeautifulSoup(resp.text, "html.parser")

    anchor = soup.find("span", id="a")
    if not anchor:
        return [], ["ESRI GDP: 見出し(id='a' 四半期別GDP速報)が見つかりません。ページ構成が変わった可能性"]

    table = anchor.find_next("table")
    if not table:
        return [], ["ESRI GDP: 見出しの次に表が見つかりません"]

    events = []
    warnings = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 3:
            continue
        period_text = tds[0].get_text(strip=True)
        if "1次速報" not in period_text:
            continue

        date_m = DATE_RE.search(tds[1].get_text(strip=True))
        time_m = TIME_RE.search(tds[2].get_text(strip=True))
        if not date_m:
            warnings.append(f"ESRI GDP: 日付を解釈できず '{period_text}' をスキップ")
            continue
        year, month, day = (int(x) for x in date_m.groups())
        hour, minute = (int(x) for x in time_m.groups()) if time_m else (8, 50)

        try:
            d = datetime.date(year, month, day)
        except ValueError:
            warnings.append(f"ESRI GDP: 不正な日付 {year}-{month}-{day} をスキップ")
            continue

        dt_jst = jst_naive_to_iso(d, hour, minute)
        events.append(make_row("jp_gdp", EVENT_DEFINITIONS["jp_gdp"], dt_jst, note=period_text))

    return events, warnings


if __name__ == "__main__":
    evs, warns = fetch_jp_gdp_events()
    for e in evs:
        print(e["datetime_jst"], e["name"], e["note"])
    for w in warns:
        print("WARNING:", w)
