"""market_radar_dashboard.html をテンプレートとして、指定日の events_YYYY-MM-DD.json を
流し込み、その日専用のダッシュボードHTML（dashboard_YYYY-MM-DD.html）を生成する。

置き換える箇所:
  1. const EVENTS = [...]; を、その日の実データに差し替え
  2. ヘッダーの日付表示を対象日に更新し、「サンプルデータ」タグを削除
  3. 「今日の要点」は自動生成せず、記入用のプレースホルダーにしておく
     （ユーザーが生成後のHTMLを開いて手動で書く運用）
"""
import datetime
import html
import json
import os
import re
import sys

TEMPLATE_PATH = "market_radar_dashboard.html"

WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]

OV_LEAD_PLACEHOLDER = "（ここに今日の要点を記入してください）"
OV_MORE_PLACEHOLDER = "（詳しい解説をここに記入してください）"

ARCHIVE_DAYS = 14
# 要約がまだ書かれていない状態を示すラベル（assemble_events.py が入れる）
PENDING_LABELS = {"要約待ち", "未取得"}


def format_date_header(d):
    return f"{d.year} / {d.month:02d} / {d.day:02d}（{WEEKDAY_JA[d.weekday()]}）"


def short_date(d):
    return f"{d.month:02d}/{d.day:02d}（{WEEKDAY_JA[d.weekday()]}）"


def load_events(d):
    """その日のevents JSONを読む。無ければNone（＝データ未生成）。"""
    path = f"events_{d.isoformat()}.json"
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def is_pending(event):
    return any(h.get("k") in PENDING_LABELS for h in event.get("highlights", []))


def render_major(d, event):
    """要約が必要な大きめのイベント（FOMC・日銀会合）を1件分。"""
    esc = html.escape
    parts = [
        '<div class="arch-major">',
        f'<div class="when">{esc(short_date(d))} {esc(event["time"])} JST</div>',
        f'<div class="ttl">{esc(event["country"])}　{esc(event["name"])}</div>',
    ]
    if is_pending(event):
        parts.append('<span class="pending">要約はまだ書かれていません</span>')
    else:
        rows = "".join(
            f'<div class="row"><div class="k">{esc(h.get("k",""))}</div>'
            f'<div class="v">{esc(h.get("v",""))}</div></div>'
            for h in event.get("highlights", [])
        )
        if rows:
            parts.append(f'<div class="arch-hl">{rows}</div>')
    parts.append("</div>")
    return "".join(parts)


def render_day_row(d, events):
    esc = html.escape
    labels = []
    for e in events:
        val = ""
        if e.get("actual") is not None:
            val = f'<span class="val">{esc(str(e["actual"]))}{esc(e.get("unit",""))}</span>'
        labels.append(f'{esc(e["country"])} {esc(e["name"])} {val}'.strip())
    body = '<span class="sep">/</span>'.join(labels)
    href = f"dashboard_{d.isoformat()}.html"
    return (
        f'<li><a href="{href}">'
        f'<span class="arch-date">{esc(short_date(d))}</span>'
        f'<span class="arch-ev">{body}</span></a></li>'
    )


def build_archive_html(target_date):
    """target_date の前日までさかのぼって ARCHIVE_DAYS 日分のまとめを作る。"""
    days = [
        target_date - datetime.timedelta(days=i)
        for i in range(ARCHIVE_DAYS, 0, -1)
    ]

    majors = []
    day_rows = []
    quiet = []

    for d in days:
        events = load_events(d)
        if events is None:
            continue
        if not events:
            quiet.append(short_date(d))
            continue
        day_rows.append(render_day_row(d, events))
        for e in events:
            if "highlights" in e:
                majors.append(render_major(d, e))

    if not day_rows and not quiet:
        return ""

    period = f"{short_date(days[0])} 〜 {short_date(days[-1])}"
    out = [f'<div class="day-label">過去{ARCHIVE_DAYS}日間のふりかえり</div>']
    out.append(f'<p class="arch-note">{html.escape(period)}　日付を押すとその日のレポートが開きます。</p>')

    if majors:
        out.append('<div class="day-label" style="margin-top:0">主要イベント（要約対象）</div>')
        out.extend(majors)

    if day_rows:
        out.append(f'<ul class="arch-list">{"".join(day_rows)}</ul>')

    if quiet:
        out.append(
            '<p class="arch-quiet">主要イベントなし: ' + "、".join(html.escape(q) for q in quiet) + "</p>"
        )

    return "".join(out)


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

    archive_html = build_archive_html(d)
    html_out, n = re.subn(
        r'(<section class="archive" id="archive">).*?(</section>)',
        lambda m: m.group(1) + archive_html + m.group(2),
        html,
        count=1,
        flags=re.DOTALL,
    )
    if n != 1:
        raise RuntimeError("テンプレート内のarchiveセクションが見つかりませんでした")
    html = html_out

    out_path = f"dashboard_{date_str}.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    return out_path, len(events)


if __name__ == "__main__":
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    out_path, n = generate(date_str)
    print(f"{date_str}: {n}件のイベントで{out_path}を生成しました。")
