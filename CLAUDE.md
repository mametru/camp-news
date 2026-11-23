# CLAUDE.md

## コミュニケーション
- 回答・作業中の説明・git の commit メッセージ・PR 本文は **日本語** で書く（コード中の識別子は英語のままでよい）。

## プロジェクト概要
キャンプギアの新製品・セール情報を自動収集する静的サイト。GitHub Actions（`.github/workflows/update.yml`）が3時間ごとに `build.py` を実行し、生成物を commit すると GitHub Pages（https://mametru.github.io/camp-news/）に反映される。詳細は `README.md`。

## 開発ルール
- Python は **標準ライブラリのみ**。外部パッケージを追加しない（サプライチェーン対策・pip 不要の方針）。
- 外部から取得した文字列は `campgear/render.py` の `e()` でエスケープし、URL は `safe_url()` を通す。
- インラインスクリプトは書かない（CSP で禁止している）。JS は `assets/` に置く。
- 変更後は `python3 -m unittest discover -s tests` を実行する。見た目の確認は `python3 build.py --no-fetch` で再生成して `index.html` を開く。
- `index.html` / `category/` / `data/` などの生成物は手で編集しない（次回の自動更新で上書きされる）。
- アフィリエイト ID・GA4 ID は `config.json` で管理する。
