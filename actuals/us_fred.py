"""FRED APIの実際に発表されたデータ(series/observations)から、
米指標の「実績値」「前回値」を取得する。

fetchers/fred.pyで使っていた release/dates（公表予定日）とは別のエンドポイント。
release/dates は将来日程を含まないことが分かったため日程取得には使わなかったが、
series/observations は実際に発表済みのデータを返すため、Phase B（当日収集）用途に合う。

日付を指定して「その日の時点で分かっていた最新2点」を取得する
（realtime_endでその日までの版に固定することで、後日の改定値を拾わないようにする）。
これにより、指標ごとの「発表月→参照対象期間」の対応をこちらで計算しなくても、
自然に「その発表日にactualとして出た値」と「その1つ前の値＝prior」が求まる。
"""
import datetime

import requests

from fetchers.common import fetch_url, get_fred_api_key

BASE = "https://api.stlouisfed.org/fred"

# event_key -> (FRED series_id, units変換, 表示単位, 小数桁, +符号を付けるか, 割り算(千人→万人等))
SERIES = {
    "us_cpi": ("CPIAUCNS", "pc1", "%", 1, False, 1),
    "us_nfp": ("PAYEMS", "chg", "万人", 1, True, 10),
    "us_pce": ("PCEPI", "pc1", "%", 1, False, 1),
    "us_gdp": ("A191RL1Q225SBEA", "lin", "%", 1, False, 1),
}


def _fetch_two_latest(series_id, units, as_of_date, api_key):
    today = datetime.date.today()
    if as_of_date > today:
        # FREDはrealtime_startに今日より先の日付を許可しない＝まだ存在しない未来のスナップショット
        return []
    try:
        resp = fetch_url(
            f"{BASE}/series/observations",
            params={
                "api_key": api_key,
                "file_type": "json",
                "series_id": series_id,
                "units": units,
                "sort_order": "desc",
                "limit": 2,
                # units変換(pc1/chg等)を使う場合、FREDの仕様上 realtime_start と
                # realtime_end は同じ日付でなければならない（=その日1時点のスナップショット）
                "realtime_start": as_of_date.isoformat(),
                "realtime_end": as_of_date.isoformat(),
            },
        )
    except requests.exceptions.HTTPError:
        return []
    return resp.json().get("observations", [])


def _fmt(raw_value, decimals, with_plus, divide):
    try:
        v = float(raw_value) / divide
    except (TypeError, ValueError):
        return None
    s = f"{v:.{decimals}f}"
    if with_plus and v > 0:
        s = "+" + s
    return s


def get_actual_prior(event_key, as_of_date):
    """戻り値: (actual_str_or_None, prior_str_or_None, unit_str)"""
    if event_key not in SERIES:
        raise ValueError(f"未対応のevent_key: {event_key}")
    series_id, units, unit_label, decimals, with_plus, divide = SERIES[event_key]

    api_key = get_fred_api_key()
    obs = _fetch_two_latest(series_id, units, as_of_date, api_key)

    valid = [o for o in obs if o.get("value") not in (None, ".", "")]
    actual = _fmt(valid[0]["value"], decimals, with_plus, divide) if len(valid) >= 1 else None
    prior = _fmt(valid[1]["value"], decimals, with_plus, divide) if len(valid) >= 2 else None
    return actual, prior, unit_label


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv

    load_dotenv()
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    d = datetime.date.fromisoformat(date_str)
    for key in SERIES:
        actual, prior, unit = get_actual_prior(key, d)
        print(f"{key}: actual={actual}{unit} prior={prior}{unit}")
