"""ISM製造業/非製造業景況指数の公表日をルールベースで計算する。

ISM（Institute for Supply Management）は民間団体で、FREDの公表日程APIでは
将来の公表日を確実に取得できない。ISM自身の実務慣行は
「製造業＝毎月の最初の営業日」「非製造業（サービス）＝毎月3番目の営業日前後」
に米東部時間10:00公表、というほぼ固定パターンのため、それをルール化して計算する。

注意: 米国の祝日は考慮していない（土日のみ除外）。祝日と重なる月はISMが
前後にずらすことがあるため、この行は "is_template" かつ note にルールベースである旨を
明記し、四半期に一度 https://www.ismworld.org/ で実際の発表日を確認することを推奨する。
"""
import datetime

from .common import us_time_to_jst_iso, make_row
from config.impact_map import EVENT_DEFINITIONS

RELEASE_HOUR_ET = 10
NOTE = "ISMは公式スケジュールAPIがないためルール計算（祝日未考慮）。四半期に一度ismworld.orgで要確認"


def _nth_business_day(year, month, n):
    d = datetime.date(year, month, 1)
    count = 0
    while True:
        if d.weekday() < 5:  # 月曜=0 ... 金曜=4
            count += 1
            if count == n:
                return d
        d += datetime.timedelta(days=1)


def _months_forward(start, count):
    y, m = start.year, start.month
    result = []
    for _ in range(count):
        result.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return result


def fetch_ism_events(months_ahead=6):
    today = datetime.date.today()
    months = _months_forward(datetime.date(today.year, today.month, 1), months_ahead)

    events = []
    for y, m in months:
        mfg_date = _nth_business_day(y, m, 1)
        dt_mfg = us_time_to_jst_iso(mfg_date, RELEASE_HOUR_ET, 0)
        events.append(make_row("us_ism_mfg", EVENT_DEFINITIONS["us_ism_mfg"], dt_mfg, note=NOTE))

        svc_date = _nth_business_day(y, m, 3)
        dt_svc = us_time_to_jst_iso(svc_date, RELEASE_HOUR_ET, 0)
        events.append(make_row("us_ism_nonmfg", EVENT_DEFINITIONS["us_ism_nonmfg"], dt_svc, note=NOTE))

    return events, []


if __name__ == "__main__":
    evs, warns = fetch_ism_events()
    for e in evs:
        print(e["datetime_jst"], e["name"])
    for w in warns:
        print("WARNING:", w)
