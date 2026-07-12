"""実績値の簡易履歴ストア。

日本側の一部の指標（全国CPI・GDP速報）は、公式ページ/PDFに「今回発表分の数値」
しか載っておらず、「前回発表分の数値」が同じ場所にない。そのため、このスクリプトが
実際に取得したactual値を毎回ここに記録しておき、次回実行時に「前回値」として
使えるようにする。初回実行時はprior（前回値）が存在しないためNoneになる。
"""
import json
import os

HISTORY_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "actuals_history.json")


def _load():
    if not os.path.exists(HISTORY_PATH):
        return {}
    with open(HISTORY_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save(data):
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)


def get_prior(event_key, before_date_iso):
    """event_keyについて、before_date_isoより前の直近の記録値を返す。無ければNone。"""
    data = _load()
    entries = data.get(event_key, [])
    past = [e for e in entries if e["date"] < before_date_iso]
    if not past:
        return None
    past.sort(key=lambda e: e["date"])
    return past[-1]["value"]


def record(event_key, date_iso, value):
    """event_keyのdate_iso時点のactual値を記録する（同じ日付があれば上書き）。"""
    if value is None:
        return
    data = _load()
    entries = data.setdefault(event_key, [])
    entries[:] = [e for e in entries if e["date"] != date_iso]
    entries.append({"date": date_iso, "value": value})
    _save(data)
