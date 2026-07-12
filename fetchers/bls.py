"""BLS（米労働統計局）公式の指標別スケジュールページから公表日程を取得する。

FRED APIのrelease/datesは将来日程を含まないことが判明したため、
発表元であるBLS自身のページを直接使う（2026-07-09時点で実ページを確認済み）。

対象ページと構造:
  https://www.bls.gov/schedule/news_release/cpi.htm     … CPI
  https://www.bls.gov/schedule/news_release/empsit.htm  … 雇用統計(Employment Situation)
  どちらも <table class="release-list"> の中に
    <tr><td>対象月(例: November 2025)</td><td>公表日(例: Dec. 18, 2025)</td><td>時刻(例: 08:30 AM)</td></tr>
  が並ぶ。時刻は米東部時間。
"""
import datetime
import re

from bs4 import BeautifulSoup

from .common import fetch_url, us_time_to_jst_iso, make_row
from config.impact_map import EVENT_DEFINITIONS

PAGES = [
    ("us_cpi", "https://www.bls.gov/schedule/news_release/cpi.htm"),
    ("us_nfp", "https://www.bls.gov/schedule/news_release/empsit.htm"),
]

DATE_RE = re.compile(r"([A-Za-z]{3})\.?\s+(\d{1,2}),\s+(\d{4})")
TIME_RE = re.compile(r"(\d{1,2}):(\d{2})\s*(AM|PM)", re.IGNORECASE)


def _parse_date(text):
    m = DATE_RE.search(text)
    if not m:
        return None
    mon_str, day, year = m.groups()
    try:
        month = datetime.datetime.strptime(mon_str, "%b").month
    except ValueError:
        return None
    try:
        return datetime.date(int(year), month, int(day))
    except ValueError:
        return None


def _parse_time(text):
    m = TIME_RE.search(text)
    if not m:
        return None
    hour, minute, ampm = m.groups()
    hour = int(hour)
    minute = int(minute)
    if ampm.upper() == "PM" and hour != 12:
        hour += 12
    if ampm.upper() == "AM" and hour == 12:
        hour = 0
    return hour, minute


def fetch_bls_events():
    events = []
    warnings = []

    for event_key, url in PAGES:
        resp = fetch_url(url)
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table", class_="release-list")
        if not table:
            warnings.append(f"BLS({event_key}): table.release-list が見つかりません。ページ構成が変わった可能性")
            continue

        for tr in table.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 3:
                continue
            date_text = tds[1].get_text(strip=True)
            time_text = tds[2].get_text(strip=True)

            d = _parse_date(date_text)
            t = _parse_time(time_text)
            if d is None:
                warnings.append(f"BLS({event_key}): 日付 '{date_text}' を解釈できずスキップ")
                continue
            hour, minute = t if t else (8, 30)

            dt_jst = us_time_to_jst_iso(d, hour, minute)
            events.append(make_row(event_key, EVENT_DEFINITIONS[event_key], dt_jst))

    return events, warnings


if __name__ == "__main__":
    evs, warns = fetch_bls_events()
    for e in evs:
        print(e["datetime_jst"], e["name"])
    for w in warns:
        print("WARNING:", w)
