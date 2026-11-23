"""アフィリエイトリンク生成。IDが未設定なら何も返さない。"""
import re
import urllib.parse

from .classify import CATEGORY_BY_SLUG

_ID_RE = re.compile(r"^[A-Za-z0-9._\-]{1,80}$")


def _valid(value):
    return bool(value) and bool(_ID_RE.match(value))


def amazon_search(query, tag):
    return "https://www.amazon.co.jp/s?" + urllib.parse.urlencode({"k": query, "tag": tag})


def rakuten_search(query, affiliate_id):
    target = "https://search.rakuten.co.jp/search/mall/" + urllib.parse.quote(query) + "/"
    q = urllib.parse.quote(target, safe="")
    return f"https://hb.afl.rakuten.co.jp/hgc/{affiliate_id}/?pc={q}&m={q}"


def product_query(item):
    """記事から商品検索キーワードを作る。特定できなければ空文字。"""
    title = item["title"]
    brand = item.get("brand", "")
    # BE-PAL新着アイテム形式「Coleman（コールマン）／コージーⅡ/C5」
    if "／" in title and item.get("source_id") == "bepal":
        maker, product = title.split("／", 1)
        maker = re.sub(r"[（(].*?[)）]", "", maker).strip()
        return f"{brand or maker} {product.strip()}"[:60]
    if not brand:
        return ""
    cat = item.get("category", "other")
    label = "キャンプ" if cat == "other" else CATEGORY_BY_SLUG[cat][1].split("・")[0]
    return f"{brand} {label}"


def links_for_item(item, cfg):
    query = product_query(item)
    if not query:
        return []
    out = []
    if _valid(cfg.get("amazon_tag")):
        out.append(("amazon", "Amazonで探す", amazon_search(query, cfg["amazon_tag"])))
    if _valid(cfg.get("rakuten_affiliate_id")):
        out.append(("rakuten", "楽天で探す", rakuten_search(query, cfg["rakuten_affiliate_id"])))
    return out


def sale_banner_links(cfg):
    out = []
    if _valid(cfg.get("amazon_tag")):
        tag = cfg["amazon_tag"]
        out.append(("amazon", "Amazon タイムセール", "https://www.amazon.co.jp/gp/goldbox?" + urllib.parse.urlencode({"tag": tag})))
        out.append(("amazon", "Amazon キャンプ用品セール", amazon_search("キャンプ用品 セール", tag)))
    if _valid(cfg.get("rakuten_affiliate_id")):
        out.append(("rakuten", "楽天 キャンプ用品セール", rakuten_search("キャンプ用品 セール", cfg["rakuten_affiliate_id"])))
    return out
