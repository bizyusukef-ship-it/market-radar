"""event_master.csv を各ソースから再構築するメインスクリプト。

実行するたびに、各fetcherが返す「直近〜将来」の日程で event_master.csv を
まるごと作り直す（フルリフレッシュ）。event_master.csv はスケジュールのみを
保持するテーブルであり、実績値等はPhase Bで別途扱うため、
毎回作り直しても過去の収集結果は失われない。

使い方:
    .venv/Scripts/python.exe build_event_master.py
"""
import csv
import datetime

from dotenv import load_dotenv

from fetchers.fomc import fetch_fomc_events
from fetchers.boj_meeting import fetch_boj_meeting_events
from fetchers.boj_tankan import fetch_boj_tankan_events
from fetchers.jp_gdp import fetch_jp_gdp_events
from fetchers.jp_cpi import fetch_jp_cpi_events
from fetchers.ism import fetch_ism_events
from fetchers.bls import fetch_bls_events
from fetchers.bea import fetch_bea_events

load_dotenv()

OUTPUT_PATH = "event_master.csv"
WINDOW_PAST_DAYS = 7
WINDOW_FUTURE_DAYS = 400

FIELDNAMES = [
    "event_id", "datetime_jst", "country", "name", "name_en",
    "impact", "category", "source_url", "is_template", "last_checked", "note",
]

FETCHERS = [
    ("FOMC", fetch_fomc_events),
    ("日銀会合", fetch_boj_meeting_events),
    ("日銀短観", fetch_boj_tankan_events),
    ("日本GDP", fetch_jp_gdp_events),
    ("日本CPI", fetch_jp_cpi_events),
    ("ISM", fetch_ism_events),
    ("BLS(米CPI/雇用統計)", fetch_bls_events),
    ("BEA(米GDP/PCE)", fetch_bea_events),
]


def in_window(row, start, end):
    d = datetime.date.fromisoformat(row["datetime_jst"][:10])
    return start <= d <= end


def main():
    today = datetime.date.today()
    start = today - datetime.timedelta(days=WINDOW_PAST_DAYS)
    end = today + datetime.timedelta(days=WINDOW_FUTURE_DAYS)

    all_events = []
    all_warnings = []

    for label, fn in FETCHERS:
        try:
            events, warnings = fn()
        except Exception as e:
            all_warnings.append(f"[{label}] 取得中に例外が発生したためスキップ: {e}")
            continue
        for w in warnings:
            all_warnings.append(f"[{label}] {w}")
        kept = [e for e in events if in_window(e, start, end)]
        all_events.extend(kept)
        print(f"[{label}] {len(events)}件取得 / うち{len(kept)}件を採用（期間内）")

    all_events.sort(key=lambda r: r["datetime_jst"])

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in all_events:
            writer.writerow(row)

    print(f"\n{OUTPUT_PATH} に {len(all_events)} 件書き込みました。")

    if all_warnings:
        print("\n--- 要確認 ---")
        for w in all_warnings:
            print("!", w)


if __name__ == "__main__":
    main()
