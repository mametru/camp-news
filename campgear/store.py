"""記事データの読み込み・統合・整理。"""
import hashlib
import json
import os
import re
import tempfile
import urllib.parse
from datetime import datetime, timedelta, timezone

from .classify import normalize

_TRACKING_PARAMS = re.compile(r"^(utm_|fbclid$|gclid$|yclid$|ref$)")


def canonical_url(url):
    parts = urllib.parse.urlsplit(url)
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True) if not _TRACKING_PARAMS.match(k)]
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc.lower(), parts.path, urllib.parse.urlencode(query), ""))


def item_id(url):
    return hashlib.sha1(canonical_url(url).encode("utf-8")).hexdigest()[:16]


def title_key(title):
    """転載記事の重複判定用。記号を除いた先頭24文字が同じなら同一記事とみなす。"""
    return re.sub(r"[\W_]+", "", normalize(title))[:24]


def load(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def save(path, items):
    """途中で落ちてもファイルが壊れないよう、一時ファイルに書いてから置き換える。"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def merge(existing, new_items, now, max_age_days, max_items):
    """新規記事を追加し、古い記事を削除する。(統合後リスト, 追加件数) を返す。"""
    by_id = {it["id"]: it for it in existing}
    seen_titles = {title_key(it["title"]) for it in existing}
    added = 0
    for it in new_items:
        key = title_key(it["title"])
        if it["id"] in by_id or key in seen_titles:
            continue
        by_id[it["id"]] = it
        seen_titles.add(key)
        added += 1

    cutoff = iso(now - timedelta(days=max_age_days))
    kept = [it for it in by_id.values() if it["published"] >= cutoff]
    kept.sort(key=lambda it: it["published"], reverse=True)
    return kept[:max_items], added


def build_item(entry, source, verdict, now):
    published = entry["published"]
    # 日時なし・未来日時は取得時刻で代用
    if published is None or published > now + timedelta(hours=1):
        published = now
    return {
        "id": item_id(entry["url"]),
        "title": entry["title"],
        "url": entry["url"],
        "summary": entry["summary"][:140],
        "source": entry.get("display_source") or source["name"],
        "source_id": source["id"],
        "kind": verdict["kind"],
        "brand": verdict["brand"],
        "category": verdict["category"],
        "published": iso(published),
        "first_seen": iso(now),
    }


def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0)
