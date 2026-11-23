"""収集 → 分類 → 保存 → サイト生成 を行うエントリポイント。

使い方:
  python build.py            # 収集してサイトを生成
  python build.py --no-fetch # 収集せず、既存データからサイトだけ再生成
"""
import argparse
import json
import os
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from campgear import render, store
from campgear.classify import CATEGORY_BY_SLUG, clean_title, classify
from campgear.fetch import FetchError, google_news_url, http_get, parse_feed

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT, "data", "items.json")
MAX_PER_GOOGLE_QUERY = 15


def load_config():
    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as f:
        return json.load(f)


def fetch_source(source, fcfg):
    url = google_news_url(source["query"]) if source["type"] == "google_news" else source["url"]
    data = http_get(url, fcfg["user_agent"], fcfg["timeout_sec"], fcfg["max_bytes"])
    entries = parse_feed(data)
    if source["type"] == "google_news":
        entries = entries[:MAX_PER_GOOGLE_QUERY]
    return entries


def collect(cfg, now):
    results, errors = [], []
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(fetch_source, s, cfg["fetch"]): s for s in cfg["sources"]}
        for fut, source in futures.items():
            try:
                entries = fut.result()
            except FetchError as exc:
                errors.append(f"{source['id']}: {exc}")
                continue
            kept = 0
            for entry in entries:
                display_source = entry["feed_source"] if source["type"] == "google_news" and entry["feed_source"] else source["name"]
                entry["title"] = clean_title(entry["title"], display_source)
                entry["display_source"] = display_source
                trusted = source.get("trusted_new_category") in entry["categories"]
                verdict = classify(entry["title"], entry["summary"], trusted_new=trusted)
                if verdict:
                    results.append(store.build_item(entry, source, verdict, now))
                    kept += 1
            print(f"  {source['id']:<18} 取得 {len(entries):>3} 件 / 採用 {kept:>3} 件")
    return results, errors


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def generate_site(cfg, items, updated_iso):
    versions = {
        "style": render.asset_version(ROOT, "assets/style.css"),
        "app": render.asset_version(ROOT, "assets/app.js"),
        "analytics": render.asset_version(ROOT, "assets/analytics.js"),
    }
    counts = Counter(it["category"] for it in items)
    write(os.path.join(ROOT, "index.html"), render.listing_page(cfg, items, items, updated_iso, versions))

    cat_dir = os.path.join(ROOT, "category")
    os.makedirs(cat_dir, exist_ok=True)
    slugs = []
    for slug in CATEGORY_BY_SLUG:
        path = os.path.join(cat_dir, f"{slug}.html")
        cat_items = [it for it in items if it["category"] == slug]
        if not cat_items:
            if os.path.exists(path):
                os.remove(path)
            continue
        slugs.append(slug)
        write(path, render.listing_page(cfg, cat_items, items, updated_iso, versions, category=slug))

    write(os.path.join(ROOT, "about.html"), render.static_page(cfg, "about", "運営者情報・広告について", render.about_html(cfg), updated_iso, versions, counts))
    write(os.path.join(ROOT, "privacy.html"), render.static_page(cfg, "privacy", "プライバシーポリシー", render.privacy_html(cfg), updated_iso, versions, counts))
    write(os.path.join(ROOT, "sitemap.xml"), render.sitemap(cfg, updated_iso, slugs))
    write(os.path.join(ROOT, "robots.txt"), render.robots(cfg))
    write(os.path.join(ROOT, "feed.xml"), render.rss(cfg, items, updated_iso))
    write(os.path.join(ROOT, ".nojekyll"), "")


def report(lines):
    """GitHub Actions の実行サマリーにも出力する。"""
    text = "\n".join(lines)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(text + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-fetch", action="store_true", help="収集をスキップして再生成のみ")
    args = parser.parse_args()

    cfg = load_config()
    now = store.now_utc()
    existing = store.load(DATA_PATH)
    errors = []
    new_items = []
    if not args.no_fetch:
        print("収集中...")
        new_items, errors = collect(cfg, now)

    items, added = store.merge(existing, new_items, now, cfg["retention"]["max_age_days"], cfg["retention"]["max_items"])
    store.save(DATA_PATH, items)
    updated_iso = store.iso(now)
    generate_site(cfg, items, updated_iso)

    kinds = Counter(it["kind"] for it in items)
    lines = [
        "## キャンプギア速報 更新結果",
        f"- 新規追加: {added} 件",
        f"- 掲載中: {len(items)} 件（新製品 {kinds.get('new', 0)} / セール {kinds.get('sale', 0)}）",
        f"- 取得エラー: {len(errors)} / {len(cfg['sources'])} ソース",
    ] + [f"  - {err}" for err in errors]
    report(lines)

    gh_out = os.environ.get("GITHUB_OUTPUT")
    if gh_out:
        with open(gh_out, "a", encoding="utf-8") as f:
            f.write(f"added={added}\n")

    # 全ソースが失敗した場合は異常終了させ、Actionsの失敗通知で気づけるようにする
    if not args.no_fetch and len(errors) == len(cfg["sources"]):
        print("全ソースの取得に失敗しました", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
