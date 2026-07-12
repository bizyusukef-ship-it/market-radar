# Market Radar — 経済イベント収集・レポート自動化 プロジェクト指示書

## このプロジェクトは何か
日本市場・米国市場の影響度の高い経済イベント（FOMC、CPI、雇用統計、日銀会合、短観など）を
カレンダーでマークし、発表当日に情報を即日収集 → AI要約 → ダッシュボードHTMLとして
レポート化するシステム。

## 全体構成（3フェーズ）
- Phase A（今ここ）: event_master構築＝イベント日程の自動取り込み
- Phase B: 発表当日の即日収集（結果値・関連報道）＋AI要約
- Phase C: ダッシュボードHTML自動生成（テンプレは完成済み）

## 完成済みの成果物
- `market_radar_dashboard.html` … レポートUIの完成テンプレート（このフォルダにある）
  - 内部の `EVENTS` 配列（JSON）を差し替えるだけで表示が変わる
  - データ契約（1イベントのフィールド定義）はHTML内のコメントに記載済み
  - 最終的には EVENTS を外部JSONから読み込むか、生成時に埋め込む形に改修してよい

## データソース方針: 無料優先
- 米国の指標日程: FRED API（セントルイス連銀、無料APIキー）
  - releases/dates 系のエンドポイントで公表日程が取れるはず。実装前に必ず
    公式ドキュメント（https://fred.stlouisfed.org/docs/api/fred/）を確認すること
- FOMC日程: FRB公式サイトの会合カレンダーページから取得
- 日本の指標日程: 公式サイトの公表予定ページから取得
  - 日銀（金融政策決定会合・短観）: boj.or.jp
  - 総務省統計局（CPI）: stat.go.jp
  - 内閣府（GDP等）: cao.go.jp / esri.cao.go.jp
- 重要: 上記ページの正確なURL・HTML構造・スケジュール形式は変わりうるので、
  実装時に必ず実ページを確認してから書くこと。推測でパースコードを書かない。
- 有料API・スクレイピング禁止サイトは使わない。robots.txtと利用規約を尊重する。

## event_master のスキーマ（CSV or SQLite、Claude Codeの提案で決めてよい）
- event_id      : 一意ID
- datetime_jst  : 発表日時（JST、ISO8601）
- country       : US / JP
- name          : イベント名（日本語表示名）
- name_en       : 英語名（ソース照合用）
- impact        : high / mid / low（主要イベントの初期値はコード内の定義表で付与）
- category      : cpi / employment / gdp / central_bank / sentiment / other
- source_url    : 日程の取得元URL
- is_template   : true=定型数値指標 / false=非定型（FOMC・日銀会合など）
- last_checked  : 日程を最終確認した日時

## 高影響イベントの初期セット（このイベントは必ずカバー）
US: FOMC（金利発表・議長会見）、CPI、雇用統計（NFP）、PCEデフレーター、
    GDP速報、ISM製造業/非製造業
JP: 日銀金融政策決定会合、日銀短観、全国CPI、GDP速報

## ダッシュボード側データ契約との対応
event_master（日程）→ 当日収集（Phase B）→ EVENTS 1件のJSONに変換:
  time / country / name / impact / unit / consensus / prior / actual /
  meaning / deep_dive[] / highlights[]（非定型のみ） / reaction / market{} / sources[]
- meaning, deep_dive, reaction は主要イベントについては辞書ファイルに事前定義してよい
  （毎回生成せず、固定解説＋当日の数値だけ差し込む方が安定する）
- highlights は非定型イベントのみ。当日の声明・報道をAI要約して生成（Phase B）
- consensus（市場予想）の無料ソースは限られる。取得可能な範囲で埋め、
  取れない場合は null として「未取得」表示にする（勝手に数値を作らない）

## 技術選定（想定・変更可）
- 言語: Python
- 依存: requests, beautifulsoup4, （必要なら）pandas
- 秘密情報: FRED APIキー等は .env に置き、コードに直書きしない。.gitignore 必須
- 実行: まず手動実行で完成させる。定期実行（タスクスケジューラ等）は動作確認後

## 進め方のルール（Claudeへ）
- 私は専門用語（リポジトリ、環境変数、venv等）に不慣れ。用語は都度かみくだいて説明する
- APIキー取得などの手順は「画面のどこを押すか」レベルで1ステップずつ案内する
- ファイルを変更する前に、何を・なぜ変えるかを一言説明する
- 一度に全部作らない。Phase Aを完成・動作確認してからPhase Bへ
- 不確かな情報（URL、API仕様）は必ず実地確認する。確認できないものは「不明」と報告する

## やらないこと
- 売買判断・投資助言の出力（レポートは公開情報の整理・要約と一般的な方向性の解説まで）
- 有料データソースの利用
- 利用規約違反となる収集
