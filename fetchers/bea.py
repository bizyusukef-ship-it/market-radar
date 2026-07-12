"""BEA（米経済分析局）の機械可読JSONから公表日程を取得する。

https://apps.bea.gov/API/signup/release_dates.json （APIキー不要、2026-07-09時点で実際に取得・確認済み）
"Gross Domestic Product" と "Personal Income and Outlays"（PCEデフレーターを含む）
のキーに、UTC時刻付きのISO8601日時リストが入っている。
"""
import datetime

from .common import fetch_url, make_row
from config.impact_map import EVENT_DEFINITIONS
from zoneinfo import ZoneInfo

URL = "https://apps.bea.gov/API/signup/release_dates.json"
JST = ZoneInfo("Asia/Tokyo")

KEYS = [
    ("us_gdp", "Gross Domestic Product"),
    ("us_pce", "Personal Income and Outlays"),
]


def fetch_bea_events():
    resp = fetch_url(URL)
    data = resp.json()

    events = []
    warnings = []
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    for event_key, json_key in KEYS:
        entry = data.get(json_key)
        if entry is None:
            warnings.append(f"BEA: キー '{json_key}' が見つかりません。JSON構成が変わった可能性")
            continue
        for date_str in entry.get("release_dates", []):
            try:
                dt_utc = datetime.datetime.fromisoformat(date_str)
            except ValueError:
                warnings.append(f"BEA({event_key}): 日時 '{date_str}' を解釈できずスキップ")
                continue
            if dt_utc < now_utc:
                continue
            dt_jst = dt_utc.astimezone(JST).isoformat()
            events.append(make_row(event_key, EVENT_DEFINITIONS[event_key], dt_jst))

    return events, warnings


if __name__ == "__main__":
    evs, warns = fetch_bea_events()
    for e in evs:
        print(e["datetime_jst"], e["name"])
    for w in warns:
        print("WARNING:", w)
