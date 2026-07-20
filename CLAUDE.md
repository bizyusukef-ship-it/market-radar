# Market Radar — 経済イベント収集・レポート自動化 プロジェクト指示書

## このプロジェクトは何か
日本市場・米国市場の影響度の高い経済イベント（FOMC、CPI、雇用統計、日銀会合、短観など）を
カレンダーでマークし、発表当日に情報を即日収集 → AI要約 → ダッシュボードHTMLとして
レポート化するシステム。

## 全体構成（3フェーズ）— すべて実装済み・稼働中（2026-07 時点）
- Phase A（完了）: event_master構築＝イベント日程の自動取り込み
- Phase B（完了）: 発表当日の即日収集（結果値・声明本文）＋AI要約
- Phase C（完了）: ダッシュボードHTML自動生成
- 自動運用（稼働中）: GitHub Actionsが毎朝6:00 JSTに全自動で更新・公開
  - 公開URL: https://bizyusukef-ship-it.github.io/market-radar/
  - 過去分は dashboard_YYYY-MM-DD.html として同じサイトに残る

## 完成済みの成果物
- `market_radar_dashboard.html` … レポートUIのテンプレート（**編集対象はこれ**）
  - 内部の `EVENTS` 配列（JSON）を `generate_dashboard.py` が差し替えて日次HTMLを生成
  - データ契約（1イベントのフィールド定義）はHTML内のコメントに記載済み
  - `<section id="archive">` に過去14日分のふりかえりが自動で差し込まれる
- 日次の生成物: `events_YYYY-MM-DD.json` → `dashboard_YYYY-MM-DD.html` → `index.html`
  - 日付入りHTMLは消さないこと。過去分の閲覧とアーカイブ表示の両方に使っている

## 過去60日間のふりかえり（アーカイブ）
`generate_dashboard.py` の `build_archive()` が、対象日の前日から60日分の
`events_*.json` を読んで生成する（`ARCHIVE_DAYS` で変更可）。
- 「主要イベント（要約対象）」= `highlights` を持つ非定型イベント（FOMC・日銀会合）。
  要約済みなら内容をその場に展開表示、未記入なら「要約はまだ書かれていません」バッジ
- その下に日別のイベントカード。**別ページに飛ばさず、その場で開いて詳細を読む**
  （テンプレートの `makeEvent()` をタイムラインと共用。データは `const ARCHIVE` に埋め込む）
- イベントが無かった日は「このほか N 日間は主要イベントなし」と件数だけ出す
- `events_*.json` が存在しない日は、勝手に「イベントなし」と断定せず単に飛ばす
- 表示は新しい日が上（降順）

### 過去分をさかのぼって埋めるとき（backfill）の注意
`assemble_events.py <過去日>` で埋め直せるが、**指標ごとに日付再現性が違う**:
- 米指標(FRED): `realtime_start/end` でその日時点のスナップショットを取るので正確
- FOMC・日銀会合: 声明URLが日付から決まるので正確
- 日銀短観: 公表日以前の最新回を選ぶ実装なので正確
- **日本のCPI・GDP: 公式ページが「最新月」しか出さないため過去日を再現できない**。
  さかのぼって実行すると当日の値が過去日に付いてしまうので、やらないこと。

## データソース方針: 無料優先
- 重要: 各ページの正確なURL・HTML構造・スケジュール形式は変わりうるので、
  修正時は必ず実ページを確認してから書くこと。推測でパースコードを書かない。
- 有料API・スクレイピング禁止サイトは使わない。robots.txtと利用規約を尊重する。

### 実際に採用したソース（実地確認済み・fetchers/配下に実装）
| 用途 | ソース | 実装 |
|---|---|---|
| FOMC日程 | FRB公式 会合カレンダー | `fetchers/fomc.py` |
| 米CPI・雇用統計 日程 | BLS公式 指標別スケジュール | `fetchers/bls.py` |
| 米GDP・PCE 日程 | BEA公式 機械可読JSON（キー不要） | `fetchers/bea.py` |
| ISM 日程 | 公式APIなし。営業日ルールで計算 | `fetchers/ism.py` |
| 日銀会合 日程 | boj.or.jp 会合カレンダー | `fetchers/boj_meeting.py` |
| 日銀短観 日程 | boj.or.jp 統計公表予定Excel | `fetchers/boj_tankan.py` |
| 日本CPI 日程 | e-Stat 統合カレンダー | `fetchers/jp_cpi.py` |
| 日本GDP 日程 | ESRI 公表予定ページ | `fetchers/jp_gdp.py` |
| 米指標の実績値 | FRED API `series/observations` | `actuals/us_fred.py` |
| 日本の実績値 | 各公式ページ/PDF/Excel | `actuals/jp_*.py` |

### 落とし穴（調査済み・繰り返さないこと）
- **FRED APIは「将来の公表日程」を持っていない**。`release/dates`は過去に発表された
  日付の記録のみ（全リリース横断で今日以降は0件と実地確認）。日程はBLS/BEA公式を使う。
  FRED APIキーは実績値取得（`series/observations`）専用。
- BLSは通常のUser-Agentだと403。ブラウザ風UAが必要（`fetchers/common.py`で設定済み）。
- **BLSはGitHub Actionsのサーバーからだとアクセス拒否される**（ローカルPCからは成功）。
  2026-07-12〜20の9日間、米CPI・雇用統計が無言で欠けたまま公開される障害が発生した。
  対策として `build_event_master.py` を**ソース単位の部分更新**に変更済み（下記）。
  BEA(apps.bea.gov)は同じ米国政府系でも問題なく取得できている。
- 日本のCPI・GDPは公式ページに「前回値」が載っていない。`actuals_history.json`に
  自前で記録を貯めて前回値を補っている。
- ISMは祝日を考慮していないルール計算。四半期に一度 ismworld.org で要確認。
- 日銀会合の公表時刻は事前非公開のため12:00を仮置きしている。

## event_master のスキーマ（CSVで確定。`event_master.csv`）
- event_id      : 一意ID（`<event_key>_<YYYY-MM-DD>` 形式）
- datetime_jst  : 発表日時（JST、ISO8601）
- country       : US / JP
- name          : イベント名（日本語表示名）
- name_en       : 英語名（ソース照合用）
- impact        : high / mid / low（`config/impact_map.py` の定義表で付与）
- category      : cpi / employment / gdp / central_bank / sentiment / other
- source_url    : 日程の取得元URL
- is_template   : True=定型数値指標 / False=非定型（FOMC・日銀会合など）
- last_checked  : 日程を最終確認した日時
- note          : 仮置き・要確認事項の注記（例「公表時刻は12:00仮置き」）

`build_event_master.py` は**ソース単位の部分更新**を行う:
- 取得に成功したソースは、そのソースが担当するevent_keyの行を差し替える
- 失敗した（例外・0件）ソースは、前回CSVの該当行をそのまま引き継ぎ、警告を大きく出す

これは「1ソースの失敗で、その指標が無言で丸ごと消える」事故（2026-07にBLSで発生）を
防ぐための設計。フルリフレッシュに戻さないこと。
保持期間は過去21日〜将来400日（過去分はアーカイブ表示に使うため14日より長くとる）。

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

## 技術選定（確定・実装済み）
- 言語: Python（仮想環境は `.venv/`。実行は `.venv\Scripts\python.exe`）
- 依存: requirements.txt 参照（requests, beautifulsoup4, openpyxl, pdfplumber, python-dotenv, tzdata）
- 秘密情報: FRED APIキーは `.env`（.gitignore済み）。GitHub Actions側はリポジトリの
  Secrets に `FRED_API_KEY` として登録済み
- 実行: GitHub Actions（`.github/workflows/daily.yml`）が毎朝6:00 JSTに自動実行

## 運用手順（重要・Claudeへ）

### 日常（自動・人は何もしない）
毎朝6:00 JSTにGitHub Actionsが自動で
`build_event_master.py` → `assemble_events.py` → `generate_dashboard.py` → `publish.py`
を実行し、結果をcommit＆pushして公開URLを更新する。数値部分はこれで埋まる。

### ユーザーから「今日の要点を書いて」「要約して」と頼まれたときの手順
自動実行では埋まらない**解説文**を、Claudeが本文を読んで書くための手順。

1. `git pull` で最新を取得（自動実行のcommitがあるため必須）
2. FOMC・日銀会合の日なら、`raw_statements/<event_id>.txt` に声明本文が保存されている。
   無ければ `python -m actuals.fomc_statement "<datetime_jst>"` 等で取得する
3. 声明本文を読み、`highlights_overrides.json` に
   `"<event_id>": [{"k":"見出し","v":"内容"}, ...]` の形で要約を追記する
4. `python assemble_events.py <日付>` → `python generate_dashboard.py <日付>`
5. 生成された `dashboard_<日付>.html` の `<p id="ov-lead">` と `<div id="ov-more">` を
   その日のEVENTSの中身を見て書き換える（＝「今日の要点」）
6. `python publish.py <日付>` で index.html に反映
7. commit して push（1〜2分後に公開URLへ反映）

### 要約を書くときの注意
- 声明本文にない内容を推測で書かない。確認できないものは「未確認」と明記する
- 例: FOMCの会見トーンは当日中に文字起こしが出ないため断定しない
- 売買判断・投資助言にならない範囲（一般的・教科書的な方向性の解説）に留める

## 進め方のルール（Claudeへ）
- 私は専門用語（リポジトリ、環境変数、venv等）に不慣れ。用語は都度かみくだいて説明する
- APIキー取得などの手順は「画面のどこを押すか」レベルで1ステップずつ案内する
- ファイルを変更する前に、何を・なぜ変えるかを一言説明する
- 一度に全部作らない。1段階ずつ完成・動作確認してから次へ
- 不確かな情報（URL、API仕様）は必ず実地確認する。確認できないものは「不明」と報告する

## 未実装・既知の制約（正直に残す）
- `consensus`（市場予想）: 信頼できる無料ソースが見つからず、常に null（「未取得」表示）。
  Investing.com等は利用規約上スクレイピング不可のため使わない方針。
- `market{}`（日経・S&P500・米10年金利・ドル円の当日反応）: 未実装。常に "—"。
- ISM製造業/非製造業の実績値: 無料の公式データソースが見つからず未実装（日程のみ）。
- 解説文の自動生成: 無人での自動生成は有料AI APIが必要なため見送り。
  ユーザーが必要な日にClaudeへ依頼する運用（上記「運用手順」参照）。

## やらないこと
- 売買判断・投資助言の出力（レポートは公開情報の整理・要約と一般的な方向性の解説まで）
- 有料データソースの利用
- 利用規約違反となる収集
