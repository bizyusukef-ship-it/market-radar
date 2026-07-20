"""event_master.csv を各ソースから再構築するメインスクリプト。

各fetcherが返す「直近〜将来」の日程で event_master.csv を作り直すが、
**ソース単位の部分更新**にしている:
- 取得に成功したソースの分だけ、そのソースが担当するevent_keyの行を差し替える
- 失敗した（例外・0件）ソースの分は、前回のCSVの行をそのまま引き継ぐ

これは実際に起きた障害への対策。BLS(bls.gov)はGitHub Actionsのサーバーからだと
アクセスを拒否されることがあり、単純なフルリフレッシュだと米CPI・雇用統計が
無言で丸ごと消えたCSVが出来てしまう（2026-07に9日間発生）。

使い方:
    .venv/Scripts/python.exe build_event_master.py
"""
import csv
import datetime
import os
import re

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
# 過去分は14日間のアーカイブ表示に使うため、余裕をみて21日分を保持する
WINDOW_PAST_DAYS = 21
WINDOW_FUTURE_DAYS = 400

FIELDNAMES = [
    "event_id", "datetime_jst", "country", "name", "name_en",
    "impact", "category", "source_url", "is_template", "last_checked", "note",
]

# (表示名, 取得関数, そのソースが担当するevent_key群)
# event_keyを明示するのは、あるソースが失敗したときに「そのソースの分だけ」
# 前回のCSVから引き継ぎ、他のソースの結果で上書きしないため。
FETCHERS = [
    ("FOMC", fetch_fomc_events, {"us_fomc"}),
    ("日銀会合", fetch_boj_meeting_events, {"jp_boj_meeting"}),
    ("日銀短観", fetch_boj_tankan_events, {"jp_tankan"}),
    ("日本GDP", fetch_jp_gdp_events, {"jp_gdp"}),
    ("日本CPI", fetch_jp_cpi_events, {"jp_cpi"}),
    ("ISM", fetch_ism_events, {"us_ism_mfg", "us_ism_nonmfg"}),
    ("BLS(米CPI/雇用統計)", fetch_bls_events, {"us_cpi", "us_nfp"}),
    ("BEA(米GDP/PCE)", fetch_bea_events, {"us_gdp", "us_pce"}),
]

EVENT_ID_RE = re.compile(r"^(.*)_(\d{4}-\d{2}-\d{2})$")


def event_key_of(row):
    m = EVENT_ID_RE.match(row["event_id"])
    return m.group(1) if m else row["event_id"]


def in_window(row, start, end):
    d = datetime.date.fromisoformat(row["datetime_jst"][:10])
    return start <= d <= end


def load_existing():
    if not os.path.exists(OUTPUT_PATH):
        return []
    with open(OUTPUT_PATH, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def main():
    today = datetime.date.today()
    start = today - datetime.timedelta(days=WINDOW_PAST_DAYS)
    end = today + datetime.timedelta(days=WINDOW_FUTURE_DAYS)

    existing = load_existing()
    all_events = []
    all_warnings = []
    failed_sources = []

    for label, fn, owned_keys in FETCHERS:
        try:
            events, warnings = fn()
        except Exception as e:
            events, warnings = [], [f"取得中に例外が発生: {e}"]

        for w in warnings:
            all_warnings.append(f"[{label}] {w}")

        kept = [e for e in events if in_window(e, start, end)]

        if kept:
            all_events.extend(kept)
            print(f"[{label}] {len(events)}件取得 / うち{len(kept)}件を採用（期間内）")
        else:
            # 取得できなかったソースは、前回CSVの該当分をそのまま引き継ぐ。
            # そうしないと、そのソースの指標が無言で丸ごと消えたCSVになる。
            carried = [
                r for r in existing
                if event_key_of(r) in owned_keys and in_window(r, start, end)
            ]
            all_events.extend(carried)
            failed_sources.append(label)
            print(f"[{label}] 取得失敗（0件）→ 前回CSVから{len(carried)}件を引き継ぎ")

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

    if failed_sources:
        # 目立つ形で出す（自動実行のログで気付けるように）
        print("\n" + "=" * 60)
        print("!!! 取得に失敗したソースがあります: " + ", ".join(failed_sources))
        print("!!! 該当分は前回CSVの日程を引き継いでいます（古い可能性あり）。")
        print("=" * 60)


if __name__ == "__main__":
    main()
