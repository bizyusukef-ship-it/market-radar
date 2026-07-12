"""FRB公式サイトのFOMC会合カレンダーページをスクレイピングする。

ページ構造（2026-07-06時点で実ページを確認済み）:
  <div class="panel panel-default">
    <div class="panel-heading"><h4><a id="...">2026 FOMC Meetings</a></h4></div>
    ... その年の各会合が続く ...
  <div class="fomc-meeting__month"><strong>January</strong></div>
  <div class="fomc-meeting__date">27-28</div>   (会見等がある会合は末尾に "*" が付く)

会合は2日間開催され、政策発表は最終日。時刻はFRBの慣例で米東部時間14:00固定。
"""
import re

from bs4 import BeautifulSoup

from .common import fetch_url, us_time_to_jst_iso, make_row
from config.impact_map import EVENT_DEFINITIONS

URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
STATEMENT_HOUR_ET = 14  # FRBの慣例：声明発表は米東部時間14:00

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}


def fetch_fomc_events():
    resp = fetch_url(URL)
    soup = BeautifulSoup(resp.text, "html.parser")

    events = []
    warnings = []
    current_year = None

    for el in soup.find_all(["h4", "div"]):
        if el.name == "h4":
            a = el.find("a")
            if a and a.text:
                m = re.match(r"(\d{4})\s+FOMC Meetings", a.text.strip())
                if m:
                    current_year = int(m.group(1))
            continue

        classes = el.get("class") or []
        if "fomc-meeting__month" in classes:
            month_name = el.get_text(strip=True)
            month = MONTHS.get(month_name)
            date_el = el.find_next_sibling("div", class_="fomc-meeting__date")
            if not date_el or month is None or current_year is None:
                warnings.append(f"FOMC: 月={month_name} の日付セルが見つからず、行をスキップ")
                continue
            date_text = date_el.get_text(strip=True).rstrip("*")
            day_text = date_text.split("-")[-1].strip()
            if not day_text.isdigit():
                warnings.append(f"FOMC: 日付テキスト '{date_text}' を解釈できずスキップ")
                continue
            day = int(day_text)

            import datetime
            try:
                decision_date = datetime.date(current_year, month, day)
            except ValueError:
                warnings.append(f"FOMC: {current_year}-{month}-{day} は不正な日付")
                continue

            dt_jst = us_time_to_jst_iso(decision_date, STATEMENT_HOUR_ET, 0)
            events.append(make_row("us_fomc", EVENT_DEFINITIONS["us_fomc"], dt_jst))

    return events, warnings


if __name__ == "__main__":
    evs, warns = fetch_fomc_events()
    for e in evs:
        print(e["datetime_jst"], e["name"])
    for w in warns:
        print("WARNING:", w)
