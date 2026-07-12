"""dashboard_YYYY-MM-DD.html を index.html にコピーする（GitHub Pages公開用の固定ファイル）。

generate_dashboard.py で生成した後、「今日の要点」を手動で書き終えてから
このスクリプトを実行する想定。index.html が常に「最新の1枚」になる。
"""
import datetime
import shutil
import sys

if __name__ == "__main__":
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.date.today().isoformat()
    src = f"dashboard_{date_str}.html"
    shutil.copyfile(src, "index.html")
    print(f"{src} を index.html にコピーしました。")
