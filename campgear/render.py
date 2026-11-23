"""静的HTML / sitemap / RSS / robots.txt の生成。

外部由来の文字列は必ず e() でエスケープし、URLは safe_url() 済みのものだけを使う。
"""
import hashlib
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from xml.sax.saxutils import escape as xml_escape

from . import affiliate
from .classify import CATEGORIES, CATEGORY_BY_SLUG, OTHER_CATEGORY
from .fetch import safe_url

JST = timezone(timedelta(hours=9))
KIND_LABEL = {"new": "新製品", "sale": "セール"}


def e(value):
    return escape(str(value or ""), quote=True)


def _parse_iso(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def jst_str(iso_str):
    return _parse_iso(iso_str).astimezone(JST).strftime("%Y/%m/%d %H:%M")


def all_categories():
    return [(c[0], c[1], c[2]) for c in CATEGORIES] + [OTHER_CATEGORY]


def asset_version(root_dir, rel):
    with open(os.path.join(root_dir, rel), "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:8]


def _csp():
    gtm = "https://www.googletagmanager.com"
    ga = "https://*.google-analytics.com https://*.analytics.google.com https://*.googletagmanager.com"
    return (
        "default-src 'self'; "
        f"script-src 'self' {gtm}; "
        f"connect-src 'self' {ga}; "
        f"img-src 'self' data: {ga}; "
        "style-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; form-action 'none'"
    )


def head(cfg, title, description, canonical, root, versions, noindex=False):
    site = cfg["site"]
    ga_id = cfg["analytics"].get("ga4_measurement_id", "")
    ga = ""
    if ga_id:
        ga = (
            f'<script async src="https://www.googletagmanager.com/gtag/js?id={e(ga_id)}"></script>\n'
            f'<script src="{root}assets/analytics.js?v={versions["analytics"]}" data-ga-id="{e(ga_id)}"></script>\n'
        )
    verify = ""
    if site.get("google_site_verification"):
        verify = f'<meta name="google-site-verification" content="{e(site["google_site_verification"])}">\n'
    robots = '<meta name="robots" content="noindex">\n' if noindex else ""
    favicon = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%F0%9F%8F%95%EF%B8%8F%3C/text%3E%3C/svg%3E"
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{_csp()}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{e(canonical)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{e(site["name"])}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:locale" content="ja_JP">
<meta name="twitter:card" content="summary">
<meta name="theme-color" content="#14532d">
{verify}{robots}<link rel="icon" href="{favicon}">
<link rel="alternate" type="application/rss+xml" title="{e(site["name"])}" href="{root}feed.xml">
<link rel="stylesheet" href="{root}assets/style.css?v={versions["style"]}">
{ga}</head>
"""


def site_header(cfg, root, updated_iso):
    site = cfg["site"]
    return f"""<body>
<div class="pr-notice">当サイトはアフィリエイト広告（PR）を利用しています。<a href="{root}about.html#ads">詳しく</a></div>
<header class="site-header">
  <div class="wrap">
    <a class="logo" href="{root}index.html">🏕️ {e(site["name"])}</a>
    <p class="tagline">{e(site["tagline"])}</p>
    <p class="updated">最終更新：<time datetime="{e(updated_iso)}">{e(jst_str(updated_iso))}</time>（自動更新）</p>
  </div>
</header>
"""


def site_footer(cfg, root, counts):
    aff = cfg["affiliate"]
    statements = []
    if affiliate._valid(aff.get("amazon_tag")):
        statements.append(f"Amazonのアソシエイトとして、{e(cfg['site']['name'])}は適格販売により収入を得ています。")
    if affiliate._valid(aff.get("rakuten_affiliate_id")):
        statements.append("当サイトは楽天アフィリエイトに参加しています。")
    stmt = "".join(f"<p>{s}</p>" for s in statements)
    cats = "".join(
        f'<li><a href="{root}category/{slug}.html">{icon} {e(label)}（{counts.get(slug, 0)}）</a></li>'
        for slug, label, icon in all_categories() if counts.get(slug)
    )
    return f"""<footer class="site-footer">
  <div class="wrap">
    <nav aria-label="カテゴリ"><h2>カテゴリ</h2><ul class="cat-links">{cats}</ul></nav>
    <nav aria-label="サイト情報" class="footer-links">
      <a href="{root}about.html">運営者情報・広告について</a>
      <a href="{root}privacy.html">プライバシーポリシー</a>
      <a href="{root}feed.xml">RSS</a>
    </nav>
    {stmt}
    <p class="disclaimer">掲載情報は各配信元の記事タイトルと概要を自動収集したものです。価格・在庫・セール期間は必ずリンク先でご確認ください。</p>
    <p class="copy">© {e(cfg["site"]["name"])}</p>
  </div>
</footer>
<script src="{root}assets/app.js?v={{APPV}}"></script>
</body>
</html>
"""


def card(item, cfg, root):
    url = safe_url(item["url"])
    if not url:
        return ""
    slug, label, icon = CATEGORY_BY_SLUG.get(item["category"], (*OTHER_CATEGORY, []))[:3]
    kind = item["kind"] if item["kind"] in KIND_LABEL else "new"
    search_blob = f'{item["title"]} {item.get("brand", "")} {item.get("source", "")}'.lower()
    brand = item.get("brand", "")
    brand_tag = f'<span class="tag tag-brand">{e(brand)}</span>' if brand else ""
    aff_links = affiliate.links_for_item(item, cfg["affiliate"])
    aff_html = ""
    if aff_links:
        btns = "".join(
            f'<a class="aff-btn aff-{e(shop)}" href="{e(href)}" target="_blank" rel="sponsored noopener" '
            f'data-ev="affiliate" data-shop="{e(shop)}">{e(text)}</a>'
            for shop, text, href in aff_links
        )
        aff_html = f'<div class="aff"><span class="pr-label">PR</span>{btns}</div>'
    summary = f'<p class="summary">{e(item["summary"])}</p>' if item.get("summary") else ""
    return f"""<article class="card" data-kind="{kind}" data-category="{e(slug)}" data-brand="{e(brand)}" data-published="{e(item["published"])}" data-search="{e(search_blob)}">
<div class="thumb cat-{e(slug)}" aria-hidden="true"><span class="thumb-icon">{icon}</span><span class="badge badge-{kind}">{KIND_LABEL[kind]}</span></div>
<div class="card-body">
<div class="meta"><span class="source">{e(item["source"])}</span><time datetime="{e(item["published"])}">{e(jst_str(item["published"]))}</time></div>
<h3 class="card-title"><a href="{e(url)}" target="_blank" rel="noopener noreferrer" data-ev="article">{e(item["title"])}</a></h3>
{summary}
<div class="tags"><a class="tag" href="{root}category/{e(slug)}.html">{icon} {e(label)}</a>{brand_tag}</div>
{aff_html}
</div>
</article>"""


def controls(items, counts, brands, show_category_filter):
    kc = Counter(it["kind"] for it in items)
    cat_buttons = ""
    if show_category_filter:
        btns = '<button type="button" class="chip active" data-cat="all">すべて</button>' + "".join(
            f'<button type="button" class="chip" data-cat="{slug}">{icon} {e(label)}</button>'
            for slug, label, icon in all_categories() if counts.get(slug)
        )
        cat_buttons = f'<div class="chips" role="group" aria-label="カテゴリで絞り込み">{btns}</div>'
    brand_opts = "".join(f'<option value="{e(b)}">{e(b)}（{n}）</option>' for b, n in brands)
    return f"""<section class="controls" aria-label="絞り込み">
<div class="tabs" role="tablist">
  <button type="button" class="tab active" data-kind="all" role="tab">すべて <span>{len(items)}</span></button>
  <button type="button" class="tab" data-kind="new" role="tab">🆕 新製品 <span>{kc.get("new", 0)}</span></button>
  <button type="button" class="tab" data-kind="sale" role="tab">🏷️ セール <span>{kc.get("sale", 0)}</span></button>
</div>
{cat_buttons}
<div class="filters">
  <label>期間 <select id="f-period"><option value="all">すべて</option><option value="1">24時間以内</option><option value="3">3日以内</option><option value="7">1週間以内</option><option value="30">30日以内</option></select></label>
  <label>ブランド <select id="f-brand"><option value="all">すべて</option>{brand_opts}</select></label>
  <label class="search">検索 <input id="f-search" type="search" placeholder="例：テント、焚き火台" autocomplete="off" maxlength="50"></label>
</div>
<p class="result-count" aria-live="polite"><span id="result-count">{len(items)}</span>件</p>
</section>"""


def sale_banner(cfg):
    links = affiliate.sale_banner_links(cfg["affiliate"])
    if not links:
        return ""
    btns = "".join(
        f'<a class="banner-btn aff-{e(shop)}" href="{e(href)}" target="_blank" rel="sponsored noopener" data-ev="affiliate" data-shop="{e(shop)}" data-placement="banner">{e(text)}</a>'
        for shop, text, href in links
    )
    return f'<section class="sale-banner"><span class="pr-label">PR</span><h2>🏷️ 開催中のセールをチェック</h2><div class="banner-links">{btns}</div></section>'


def listing_page(cfg, items, all_items, updated_iso, versions, category=None):
    root = "../" if category else ""
    site = cfg["site"]
    counts = Counter(it["category"] for it in all_items)
    brands = Counter(it["brand"] for it in items if it.get("brand")).most_common(40)
    if category:
        slug, label, icon = CATEGORY_BY_SLUG[category][:3]
        title = f"{label}の新製品・セール情報 | {site['name']}"
        desc = f"{label}の新製品・新作とセール情報を毎日自動でまとめています。（{len(items)}件）"
        canonical = f"{site['base_url']}category/{slug}.html"
        h1 = f"{icon} {label}の新製品・セール情報"
    else:
        title = f"{site['name']}｜キャンプ・アウトドアギアの新製品とセール情報"
        desc = site["tagline"] + f"。スノーピーク、コールマン、DODなど{len(items)}件掲載。"
        canonical = site["base_url"]
        h1 = "キャンプギアの新製品・セール情報"
    cards = "\n".join(card(it, cfg, root) for it in items)
    empty = '<p class="empty" id="empty" hidden>条件に一致する記事がありません。</p>'
    body = f"""<main class="wrap">
<h1 class="page-title">{e(h1)}</h1>
{sale_banner(cfg)}
{controls(items, counts, brands, show_category_filter=not category)}
<div class="grid" id="grid">
{cards}
</div>
{empty}
<div class="more-wrap"><button type="button" id="more" class="more" hidden>もっと見る</button></div>
</main>
"""
    return head(cfg, title, desc, canonical, root, versions) + site_header(cfg, root, updated_iso) + body + site_footer(cfg, root, counts).replace("{APPV}", versions["app"])


def static_page(cfg, slug, title, inner_html, updated_iso, versions, counts):
    site = cfg["site"]
    canonical = f"{site['base_url']}{slug}.html"
    return (
        head(cfg, f"{title} | {site['name']}", f"{site['name']}の{title}", canonical, "", versions)
        + site_header(cfg, "", updated_iso)
        + f'<main class="wrap prose"><h1 class="page-title">{e(title)}</h1>{inner_html}</main>\n'
        + site_footer(cfg, "", counts).replace("{APPV}", versions["app"])
    )


def about_html(cfg):
    site = cfg["site"]
    contact = safe_url(site.get("contact_url", ""))
    contact_html = f'<a href="{e(contact)}" target="_blank" rel="noopener">こちら</a>' if contact else "サイト内でお知らせします"
    return f"""
<h2>このサイトについて</h2>
<p>{e(site["name"])}は、キャンプ・アウトドアギアの新製品とセール情報を、各メーカーのプレスリリースやアウトドアメディア、ニュースサイトから自動で収集し、一覧にまとめているサイトです。数時間ごとに自動で更新しています。</p>
<p>各記事の内容・著作権は配信元に帰属します。当サイトはタイトル・概要の引用とリンクのみを掲載し、記事本文や画像は転載していません。掲載に問題がある場合はご連絡ください。速やかに対応します。</p>
<h2 id="ads">広告について（PR表記）</h2>
<p>当サイトは、Amazonアソシエイト・楽天アフィリエイト等のアフィリエイトプログラムに参加する場合があり、「PR」と表示したリンクから商品を購入されると、当サイトに紹介料が支払われることがあります。商品の価格・在庫・セール内容は各販売サイトでご確認ください。</p>
<h2>免責事項</h2>
<p>掲載情報は自動収集のため、誤りや古い情報が含まれる場合があります。当サイトの情報を利用したことにより生じた損害について、当サイトは責任を負いかねます。</p>
<h2>運営者・お問い合わせ</h2>
<p>運営：{e(site.get("operator", site["name"]))}</p>
<p>お問い合わせは{contact_html}からお願いします。</p>
"""


def privacy_html(cfg):
    return f"""
<p>{e(cfg["site"]["name"])}（以下「当サイト」）における利用者情報の取り扱いについて定めます。</p>
<h2>アクセス解析ツールについて</h2>
<p>当サイトでは、Googleによるアクセス解析ツール「Google アナリティクス（GA4）」を利用しています。Google アナリティクスはデータ収集のためにCookieを使用します。このデータは匿名で収集されており、個人を特定するものではありません。</p>
<p>この機能はブラウザのCookie設定を無効にすることで収集を拒否できます。また、<a href="https://tools.google.com/dlpage/gaoptout?hl=ja" target="_blank" rel="noopener">Google アナリティクス オプトアウト アドオン</a>でも無効化できます。詳しくは<a href="https://marketingplatform.google.com/about/analytics/terms/jp/" target="_blank" rel="noopener">Google アナリティクス利用規約</a>および<a href="https://policies.google.com/technologies/partner-sites?hl=ja" target="_blank" rel="noopener">Googleのポリシーと規約</a>をご覧ください。</p>
<h2>アフィリエイトプログラムについて</h2>
<p>当サイトは、Amazonアソシエイト・楽天アフィリエイト等のアフィリエイトプログラムに参加する場合があります。これらのプログラムでは、商品の紹介・購入の計測のためにCookieが使用されることがあります。</p>
<h2>免責事項</h2>
<p>当サイトからのリンク先で提供される情報・サービスについて、当サイトは責任を負いません。</p>
<h2>改定</h2>
<p>本ポリシーは必要に応じて改定することがあります。改定後の内容は本ページに掲載した時点から効力を生じます。</p>
"""


def sitemap(cfg, updated_iso, category_slugs):
    base = cfg["site"]["base_url"]
    urls = [base] + [f"{base}category/{s}.html" for s in category_slugs] + [f"{base}about.html", f"{base}privacy.html"]
    body = "".join(f"<url><loc>{xml_escape(u)}</loc><lastmod>{updated_iso}</lastmod></url>" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>\n'


def robots(cfg):
    return f"User-agent: *\nAllow: /\nSitemap: {cfg['site']['base_url']}sitemap.xml\n"


def rss(cfg, items, updated_iso):
    site = cfg["site"]
    from email.utils import format_datetime
    entries = []
    for it in items[:50]:
        url = safe_url(it["url"])
        if not url:
            continue
        entries.append(
            "<item>"
            f"<title>{xml_escape('【' + KIND_LABEL.get(it['kind'], '') + '】' + it['title'])}</title>"
            f"<link>{xml_escape(url)}</link>"
            f'<guid isPermaLink="false">{xml_escape(it["id"])}</guid>'
            f"<pubDate>{format_datetime(_parse_iso(it['published']))}</pubDate>"
            f"<description>{xml_escape(it.get('summary', ''))}</description>"
            "</item>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
        f"<title>{xml_escape(site['name'])}</title><link>{xml_escape(site['base_url'])}</link>"
        f"<description>{xml_escape(site['tagline'])}</description><language>ja</language>"
        f"<lastBuildDate>{format_datetime(_parse_iso(updated_iso))}</lastBuildDate>"
        + "".join(entries)
        + "</channel></rss>\n"
    )
