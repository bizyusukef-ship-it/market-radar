"""fetchers共通のヘルパー関数。"""
import datetime
import os
from zoneinfo import ZoneInfo

import requests

JST = ZoneInfo("Asia/Tokyo")
EASTERN = ZoneInfo("America/New_York")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "market-radar-research/1.0 (personal, non-commercial use)"
)

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})


def fetch_url(url, params=None, timeout=20):
    resp = session.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    if resp.encoding is None or resp.encoding.lower() == "iso-8859-1":
        resp.encoding = resp.apparent_encoding
    return resp


def us_time_to_jst_iso(date_obj, hour, minute):
    """米東部時間の日付＋時刻をJSTのISO8601文字列に変換する。"""
    dt_et = datetime.datetime(
        date_obj.year, date_obj.month, date_obj.day, hour, minute, tzinfo=EASTERN
    )
    return dt_et.astimezone(JST).isoformat()


def jst_naive_to_iso(date_obj, hour, minute):
    """日本時間の日付＋時刻（すでにJST）をISO8601文字列に変換する。"""
    dt = datetime.datetime(
        date_obj.year, date_obj.month, date_obj.day, hour, minute, tzinfo=JST
    )
    return dt.isoformat()


def get_fred_api_key():
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise RuntimeError(
            ".envにFRED_API_KEYが設定されていません。fredaccount.stlouisfed.org/apikeys で取得してください"
        )
    return key


def make_row(event_key, definition, datetime_jst_iso, source_url=None, note=None):
    """event_masterの1行分の辞書を作る。"""
    date_part = datetime_jst_iso[:10]
    return {
        "event_id": f"{event_key}_{date_part}",
        "datetime_jst": datetime_jst_iso,
        "country": definition["country"],
        "name": definition["name"],
        "name_en": definition["name_en"],
        "impact": definition["impact"],
        "category": definition["category"],
        "source_url": source_url or definition["source_url"],
        "is_template": definition["is_template"],
        "last_checked": datetime.datetime.now(JST).isoformat(),
        "note": note or "",
    }
