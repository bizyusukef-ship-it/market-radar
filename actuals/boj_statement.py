"""日銀 金融政策決定会合の決定内容（声明PDF）の本文を取得する。

fetchers/boj_meeting.pyで確認済みのURL規則
https://www.boj.or.jp/mopo/mpmdeci/mpr_{year}/k{yymmdd}a.pdf
（{yymmdd}は会合最終日＝決定日）からPDFを取得し、テキストを抽出する。

FOMCと同様、ここではPDF本文を正確に取ってくるところまでに役割を絞り、
highlights欄への要約はAI（Claude）が本文を読んで作成する。
"""
import datetime
import io

import pdfplumber
import requests

from fetchers.common import fetch_url


def fetch_statement_text(datetime_jst_iso):
    d = datetime.datetime.fromisoformat(datetime_jst_iso).date()
    yymmdd = d.strftime("%y%m%d")
    url = f"https://www.boj.or.jp/mopo/mpmdeci/mpr_{d.year}/k{yymmdd}a.pdf"

    try:
        resp = fetch_url(url)
    except requests.exceptions.HTTPError:
        return None, url

    with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return text, url


if __name__ == "__main__":
    import sys

    dt_iso = sys.argv[1] if len(sys.argv) > 1 else None
    if not dt_iso:
        print("usage: python -m actuals.boj_statement <datetime_jst ISO8601>")
        raise SystemExit(1)
    text, url = fetch_statement_text(dt_iso)
    print("URL:", url)
    print("---")
    print(text)
