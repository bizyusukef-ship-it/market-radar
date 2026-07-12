"""market_radar_dashboard.html をテンプレートとして、指定日の events_YYYY-MM-DD.json を
流し込み、その日専用のダッシュボードHTML（dashboard_YYYY-MM-DD.html）を生成する。

置き換える箇所:
  1. const EVENTS = [...]; を、その日の実データに差し替え
  2. ヘッダーの日付表示を対象日に更新し、「サンプルデータ」タグを削除
  3. 「今日の要点」は自動生成せず、記入用のプレースホルダーにしておく
     （ユーザーが生成後のHTMLを開いて手動で書く運用）
"""
import datetime
import json
import re
import sys

TEMPLATE_PATH = "market_radar_dashboard.html"

WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]

OV_LEAD_PLACEHOLDER = "（ここに今日の要点を記入してください）"
OV_MORE_PLACEHOLDER = "（詳しい解説をここに記入してください）"


def format_date_header(d):
    return f"{d.year} / {d.month:02d} / {d.day:02d}（{WEEKDAY_JA[d.weekday()]}）"


def generate(date_str):
    d = datetime.date.fromisoformat(date_str)
    events_path = f"events_{date_str}.json"

    with open(events_path, encoding="utf-8") as f:
        events = json.load(f)
    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        html = f.read()

    events_js = json.dumps(events, ensure_ascii=False, indent=2)
    html, n = re.subn(
        r"const EVENTS = \[.*?\];",
        f"const EVENTS = {events_js};",
        html,
        count=1,
        flags=re.DOTALL,
    )
    if n != 1:
        raise RuntimeError("テンプレート内のEVENTS配列が見つかりませんでした")

    html, n = re.subn(
        r'<div class="date num" id="today">.*?</div>',
        f'<div class="date num" id="today">{format_date_header(d)}</div>',
        html,
        count=1,
    )
    if n != 1:
        raise RuntimeError("テンプレート内の日付表示が見つかりませんでした")

    html = re.sub(r'\s*<span class="sample-tag">.*?</span>', "", html, count=1)
    html = html.replace("（現在はサンプル表示）", "")

    html, n = re.subn(
        r'(<p id="ov-lead">).*?(</p>)',
        rf"\1{OV_LEAD_PLACEHOLDER}\2",
        html,
        count=1,
        flags=re.DOTALL,
    )
    if n != 1:
        raise RuntimeError("テンプレート内のov-leadが見つかりませんでした")

    html, n = re.subn(
        r'(<div class="more" id="ov-more">).*?(</div>)',
        rf"\1\n      {OV_MORE_PLACEHOLDER}\n    \2",
        html,
        count=1,
        flags=re.DOTALL,
    )
    if n != 1:
        raise RuntimeError("テンプレート内のov-moreが見つかりませんでした")

    out_path = f"dashboard_{date_str}.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path, len(events)


if __name__ == "__main__":
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    out_path, n = generate(date_str)
    print(f"{date_str}: {n}件のイベントで{out_path}を生成しました。")
