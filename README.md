# キャンプギア新製品・セール速報

キャンプ・アウトドアギアの **新製品** と **セール情報** を自動収集し、静的サイトとして公開します。
GitHub Actions が3時間ごとに収集 → 生成 → コミットし、GitHub Pages で配信されます。

## 構成

```
build.py              エントリポイント（収集 → 分類 → 保存 → サイト生成）
config.json           サイト設定・GA4・アフィリエイトID・情報源
campgear/
  fetch.py            フィード取得・パース（壊れたXMLにも対応）
  classify.py         キャンプ関連判定 / 新製品・セール判定 / ブランド・カテゴリ分類
  store.py            重複排除・90日より古い記事の削除
  affiliate.py        Amazon・楽天の商品検索リンク生成
  render.py           HTML / sitemap.xml / feed.xml / robots.txt 生成（全出力をエスケープ）
assets/               style.css / app.js（絞り込み・GA4イベント） / analytics.js（GA4初期化）
data/items.json       記事データ（自動更新）
tests/                ユニットテスト
```

生成物：`index.html`, `category/*.html`, `about.html`, `privacy.html`, `sitemap.xml`, `feed.xml`, `robots.txt`

外部ライブラリは使っていません（Python 3.10+ の標準ライブラリのみ）。

## ローカルで動かす

```sh
python3 build.py             # 収集してサイト生成
python3 build.py --no-fetch  # 収集せず再生成だけ（デザイン調整時など）
python3 -m unittest discover -s tests
```

生成された `index.html` をブラウザで開けば確認できます。

## 収益化の設定

`config.json` の `affiliate` にIDを入れると、ブランドや商品名を判別できた記事カードとセールバナーに「PR」付きの検索リンクが自動で表示されます。空欄なら非表示です。

| 項目 | 値の例 | 取得先 |
|---|---|---|
| `amazon_tag` | `xxxxx-22` | Amazonアソシエイト |
| `rakuten_affiliate_id` | `1a2b3c4d.5e6f7a8b.1a2b3c4d.5e6f7a8b` | 楽天アフィリエイト |

広告表記（ステマ規制対応）、Amazonアソシエイトの必須文言、プライバシーポリシーは自動で出力されます。

## GA4 で見られるもの

測定ID は `config.json` の `analytics.ga4_measurement_id`。自動で送信されるイベント：

| イベント | 発生タイミング | パラメータ |
|---|---|---|
| `page_view` | ページ表示（自動） | |
| `click_article` | 記事リンクのクリック | kind, category, brand, source, link_domain |
| `click_affiliate` | Amazon/楽天リンクのクリック | shop, placement, kind, category, brand |
| `filter_change` | タブ・カテゴリ・期間・ブランドの切替 | filter_type, filter_value |
| `search` | サイト内検索 | search_term |
| `load_more` | 「もっと見る」 | shown |

GA4 管理画面での推奨設定：
1. **管理 → カスタム定義** で `kind`, `category`, `brand`, `shop`, `placement`, `filter_type`, `filter_value` をイベントスコープのカスタムディメンションとして登録
2. **管理 → イベント** で `click_affiliate` を「キーイベント」に設定（収益に直結する指標）

## 情報源の追加・調整

- `config.json` の `sources` に RSS（`type: "rss"`）か Googleニュース検索（`type: "google_news"`）を追加
- ブランド・カテゴリ・除外語は `campgear/classify.py` の定数を編集
