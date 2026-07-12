"""日本銀行 金融政策決定会合の開催日程ページをスクレイピングする。

ページ構造（2026-07-06時点で実ページを確認済み）:
  <h2 id="p2026">2026年</h2>
  <table>...<tbody><tr><td>1月22日（木）・23日（金） [PDF ...]</td>...</tr></tbody></table>
  <h2 id="p2025">2025年</h2>
  <table>...</table>

1つ目の<td>が会合の開催日（初日・最終日）。政策公表は最終日に行われる。
「4月30日（水）・5月 1日（木）」のように月をまたぐ書き方もあるため、
月の指定がない側の日付は直前に出てきた月を引き継ぐ。

公表の正確な時刻は事前には公開されていない（会合終了後、随時）ため、
ここでは目安として12:00を仮置きし、note欄に「時刻は目安」と明記する。
"""
import datetime
import re

from bs4 import BeautifulSoup

from .common import fetch_url, jst_naive_to_iso, make_row
from config.impact_map import EVENT_DEFINITIONS

URL = "https://www.boj.or.jp/mopo/mpmsche_minu/index.htm"
PLACEHOLDER_HOUR = 12
PLACEHOLDER_MINUTE = 0

YEAR_HEADING_RE = re.compile(r"^p(\d{4})$")
DATE_RE = re.compile(r"(?:(\d{1,2})月\s*)?(\d{1,2})日")


def _parse_decision_date(cell_text, year):
    cleaned = re.sub(r"\[PDF.*?\]", "", cell_text)
    matches = DATE_RE.findall(cleaned)
    if not matches:
        return None
    month = None
    day = None
    for mo, da in matches:
        if mo:
            month = int(mo)
        day = int(da)
    if month is None or day is None:
        return None
    try:
        return datetime.date(year, month, day)
    except ValueError:
        return None


def fetch_boj_meeting_events():
    resp = fetch_url(URL)
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    warnings = []
    current_year = None

    for el in soup.find_all(["h2", "table"]):
        if el.name == "h2":
            m = YEAR_HEADING_RE.match(el.get("id") or "")
            current_year = int(m.group(1)) if m else None
            continue

        if current_year is None:
            continue

        tbody = el.find("tbody")
        if not tbody:
            continue
        for tr in tbody.find_all("tr"):
            first_td = tr.find("td")
            if not first_td:
                continue
            text = first_td.get_text(" ", strip=True)
            decision_date = _parse_decision_date(text, current_year)
            if decision_date is None:
                warnings.append(f"BOJ会合: '{text}' から日付を解釈できずスキップ")
                continue
            dt_jst = jst_naive_to_iso(decision_date, PLACEHOLDER_HOUR, PLACEHOLDER_MINUTE)
            events.append(
                make_row(
                    "jp_boj_meeting",
                    EVENT_DEFINITIONS["jp_boj_meeting"],
                    dt_jst,
                    note="公表時刻は未確定のため12:00を仮置き。当日Phase Bで確定要",
                )
            )
        current_year = None  # 1テーブル処理したら次のh2まで無効化

    return events, warnings


if __name__ == "__main__":
    evs, warns = fetch_boj_meeting_events()
    for e in evs:
        print(e["datetime_jst"], e["name"], e["note"])
    for w in warns:
        print("WARNING:", w)
