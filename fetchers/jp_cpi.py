"""e-Stat（政府統計の総合窓口）の公表予定一覧から、全国CPIの公表日を取得する。

https://www.e-stat.go.jp/release-calendar に toukeiCd（統計コード）と
日付範囲（startYear等）をクエリで渡すと、その統計の公表予定だけを絞り込める
（2026-07-06時点で実ページを確認済み）。CPIのtoukeiCdは00200573。

このカレンダーには「消費者物価指数 全国(YYYY年M月分)」（毎月の本来の発表）に加えて、
「消費者物価指数 東京都区部...」（東京都区部の先行速報、対象外）や
「...基準改定に伴う遡及結果...」（不定期の特別公表、対象外）も混在するため、
タイトルを正規表現で絞り込む。
"""
import datetime
import re

from bs4 import BeautifulSoup

from .common import fetch_url, jst_naive_to_iso, make_row
from config.impact_map import EVENT_DEFINITIONS

URL = "https://www.e-stat.go.jp/release-calendar"
TOUKEI_CD = "00200573"

TITLE_RE = re.compile(r"^消費者物価指数\s*全国\(\d{4}年\d{1,2}月分")
DATETIME_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})\s*(\d{1,2}):(\d{2})")


def fetch_jp_cpi_events(months_ahead=8):
    today = datetime.date.today()
    end = today + datetime.timedelta(days=30 * months_ahead)
    params = {
        "toukeiCd": TOUKEI_CD,
        "startYear": today.year,
        "startMonth": today.month,
        "startDay": 1,
        "endYear": end.year,
        "endMonth": end.month,
        "endDay": end.day,
    }
    resp = fetch_url(URL, params=params)
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    warnings = []
    for li in soup.find_all("li", class_="stat-list-row"):
        title_el = li.find("span", class_="stat-announce-comment")
        day_el = li.find("span", class_="stat-announce-keisaiday")
        if not title_el or not day_el:
            continue
        title = title_el.get_text(strip=True)
        if not TITLE_RE.match(title):
            continue

        m = DATETIME_RE.search(day_el.get_text(" ", strip=True))
        if not m:
            warnings.append(f"e-Stat CPI: 公表日時を解釈できず '{title}' をスキップ")
            continue
        year, month, day, hour, minute = (int(x) for x in m.groups())
        try:
            d = datetime.date(year, month, day)
        except ValueError:
            warnings.append(f"e-Stat CPI: 不正な日付 {year}-{month}-{day} をスキップ")
            continue

        dt_jst = jst_naive_to_iso(d, hour, minute)
        events.append(make_row("jp_cpi", EVENT_DEFINITIONS["jp_cpi"], dt_jst))

    return events, warnings


if __name__ == "__main__":
    evs, warns = fetch_jp_cpi_events()
    for e in evs:
        print(e["datetime_jst"], e["name"])
    for w in warns:
        print("WARNING:", w)
