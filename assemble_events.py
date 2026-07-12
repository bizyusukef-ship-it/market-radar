"""指定した日付のイベントについて、event_master.csv + 実績値 + 声明要約 + 固定解説を
合体させ、market_radar_dashboard.html の EVENTS 配列と同じ形のJSONを組み立てる。

定型イベント（is_template=True）: 実績値は actuals/ 配下のモジュールで自動取得。
非定型イベント（is_template=False、FOMC・日銀会合）: 声明の生テキストを取得して
raw_statements/ に保存するところまでを自動化する。要約（highlights）は
highlights_overrides.json に人（またはClaude）が書いたものがあればそれを使う。
無ければ highlights は空のまま「要約待ち」の注記を付ける。

consensus（市場予想）は信頼できる無料ソースが無いため、常にnull（未取得）とする。
market（日経・S&P・金利・ドル円の当日反応）は今回のスコープ外のため "—" 固定。
"""
import csv
import datetime
import json
import os
import re
import sys

from dotenv import load_dotenv

from actuals import us_fred, jp_cpi as jp_cpi_actual, jp_gdp as jp_gdp_actual, jp_tankan as jp_tankan_actual
from actuals import fomc_statement, boj_statement
from config.event_dictionary import EVENT_DICTIONARY

load_dotenv()

EVENT_MASTER_PATH = "event_master.csv"
OVERRIDES_PATH = "highlights_overrides.json"
RAW_STATEMENTS_DIR = "raw_statements"

EVENT_ID_RE = re.compile(r"^(.*)_(\d{4}-\d{2}-\d{2})$")

US_FRED_KEYS = {"us_cpi", "us_nfp", "us_pce", "us_gdp"}
JP_ACTUAL_FETCHERS = {
    "jp_cpi": jp_cpi_actual.fetch_jp_cpi_actual,
    "jp_gdp": jp_gdp_actual.fetch_jp_gdp_actual,
    "jp_tankan": jp_tankan_actual.fetch_jp_tankan_actual,
}
STATEMENT_FETCHERS = {
    "us_fomc": fomc_statement.fetch_statement_text,
    "jp_boj_meeting": boj_statement.fetch_statement_text,
}

PLACEHOLDER_MARKET = {"nikkei": "—", "sp500": "—", "us10y": "—", "usdjpy": "—"}


def load_overrides():
    if not os.path.exists(OVERRIDES_PATH):
        return {}
    with open(OVERRIDES_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_actual_prior_unit(event_key, target_date):
    if event_key in US_FRED_KEYS:
        return us_fred.get_actual_prior(event_key, target_date)
    if event_key in JP_ACTUAL_FETCHERS:
        return JP_ACTUAL_FETCHERS[event_key](target_date)
    return None, None, ""


def build_sources(row, event_key):
    sources = [f"{row['name_en']} 公表スケジュール {row['source_url']}"]
    if event_key in US_FRED_KEYS:
        sources.append(f"{row['name_en']} 実績値(FRED) https://fred.stlouisfed.org/series/{us_fred.SERIES[event_key][0]}")
    return sources


def _minimal_event(row):
    """組み立てに失敗したイベントの、実績値なしの最低限の枠。"""
    m = EVENT_ID_RE.match(row["event_id"])
    event_key = m.group(1) if m else row["event_id"]
    dic = EVENT_DICTIONARY.get(event_key, {"meaning": "", "deep_dive": [], "reaction": ""})
    return {
        "time": row["datetime_jst"][11:16],
        "country": row["country"],
        "name": row["name"],
        "impact": row["impact"],
        "unit": "",
        "consensus": None,
        "prior": None,
        "actual": None,
        "meaning": dic["meaning"],
        "deep_dive": dic["deep_dive"],
        "reaction": dic["reaction"],
        "market": PLACEHOLDER_MARKET,
        "sources": build_sources(row, event_key),
    }


def assemble_event(row, overrides):
    m = EVENT_ID_RE.match(row["event_id"])
    event_key = m.group(1) if m else row["event_id"]
    target_date = datetime.date.fromisoformat(row["datetime_jst"][:10])
    dic = EVENT_DICTIONARY.get(event_key, {"meaning": "", "deep_dive": [], "reaction": ""})

    event = {
        "time": row["datetime_jst"][11:16],
        "country": row["country"],
        "name": row["name"],
        "impact": row["impact"],
        "unit": "",
        "consensus": None,
        "prior": None,
        "actual": None,
        "meaning": dic["meaning"],
        "deep_dive": dic["deep_dive"],
        "reaction": dic["reaction"],
        "market": PLACEHOLDER_MARKET,
        "sources": build_sources(row, event_key),
    }

    if row["is_template"] == "True":
        actual, prior, unit = get_actual_prior_unit(event_key, target_date)
        event["actual"] = actual
        event["prior"] = prior
        event["unit"] = unit
    else:
        override = overrides.get(row["event_id"])
        if override:
            event["highlights"] = override
        else:
            fetcher = STATEMENT_FETCHERS.get(event_key)
            if fetcher:
                text, url = fetcher(row["datetime_jst"])
                if text:
                    os.makedirs(RAW_STATEMENTS_DIR, exist_ok=True)
                    path = os.path.join(RAW_STATEMENTS_DIR, f"{row['event_id']}.txt")
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    event["highlights"] = [
                        {"k": "要約待ち", "v": f"声明本文を{path}に保存しました。{OVERRIDES_PATH}にhighlightsを追記してください（元テキスト: {url}）"}
                    ]
                else:
                    event["highlights"] = [{"k": "未取得", "v": f"声明ページがまだ見つかりません（{url}）"}]
            else:
                event["highlights"] = []

    return event


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()

    overrides = load_overrides()
    with open(EVENT_MASTER_PATH, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["datetime_jst"].startswith(date_str)]

    # 無人の自動実行でも、1件のイベント取得が失敗しただけで全体が止まらないよう、
    # イベントごとに例外を握りつぶす（失敗分は実績値null=未取得のまま最低限の枠で出す）。
    events = []
    for r in rows:
        try:
            events.append(assemble_event(r, overrides))
        except Exception as e:
            print(f"! {r['event_id']} の組み立てに失敗（スキップせず枠のみ出力）: {e}")
            events.append(_minimal_event(r))
    events.sort(key=lambda e: e["time"])

    out_path = f"events_{date_str}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

    print(f"{date_str}: {len(events)}件のイベントを{out_path}に書き出しました。")
    for e in events:
        print(" -", e["time"], e["country"], e["name"])


if __name__ == "__main__":
    main()
