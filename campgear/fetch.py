"""フィード取得とパース（標準ライブラリのみ）。"""
import email.utils
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html.parser import HTMLParser

NS = {
    "rss1": "http://purl.org/rss/1.0/",
    "dc": "http://purl.org/dc/elements/1.1/",
}


_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufffe\uffff]")


class FetchError(Exception):
    pass


def http_get(url, user_agent, timeout, max_bytes):
    if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
        raise FetchError(f"unsupported scheme: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:  # noqa: S310 (scheme checked above)
            if res.status != 200:
                raise FetchError(f"HTTP {res.status}")
            data = res.read(max_bytes + 1)
    except FetchError:
        raise
    except Exception as exc:  # ネットワーク系の例外はまとめて呼び出し元へ
        raise FetchError(f"{type(exc).__name__}: {exc}") from exc
    if len(data) > max_bytes:
        raise FetchError("response too large")
    return data


def google_news_url(query):
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}+when:14d&hl=ja&gl=JP&ceid=JP:ja"


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def strip_html(text):
    """HTMLタグを取り除いたプレーンテキストを返す（表示時は別途エスケープする）。"""
    if not text:
        return ""
    p = _TextExtractor()
    try:
        p.feed(text)
        p.close()
        out = "".join(p.parts)
    except Exception:
        out = re.sub(r"<[^>]+>", " ", text)
    out = html.unescape(out)
    out = _CONTROL_CHARS.sub("", out)  # XML(RSS)で使えない制御文字を除去
    return re.sub(r"\s+", " ", out).strip()


def parse_date(value):
    """RFC822 / ISO8601 を timezone付き datetime(UTC) に。失敗時 None。"""
    if not value:
        return None
    value = value.strip()
    dt = None
    try:
        dt = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def safe_url(url):
    """http(s) の絶対URLだけ通す。"""
    url = (url or "").strip()
    parts = urllib.parse.urlsplit(url)
    if parts.scheme in ("http", "https") and parts.netloc:
        return url
    return ""


def _entry(title, link, published, summary, categories, source):
    return {
        "title": strip_html(title),
        "url": safe_url(link),
        "published": parse_date(published),
        "summary": strip_html(summary)[:400],
        "categories": [strip_html(c) for c in categories if c],
        "feed_source": strip_html(source),
    }


def _parse_etree(data):
    root = ET.fromstring(data)
    entries = []
    channel = root.find("channel")
    if channel is not None:  # RSS 2.0
        for it in channel.findall("item"):
            src = it.find("source")
            entries.append(_entry(
                it.findtext("title"), it.findtext("link"),
                it.findtext("pubDate") or it.findtext("dc:date", namespaces=NS),
                it.findtext("description"),
                [c.text for c in it.findall("category")],
                src.text if src is not None else "",
            ))
        return entries
    for it in root.findall("rss1:item", NS):  # RSS 1.0 (RDF)
        entries.append(_entry(
            it.findtext("rss1:title", namespaces=NS), it.findtext("rss1:link", namespaces=NS),
            it.findtext("dc:date", namespaces=NS), it.findtext("rss1:description", namespaces=NS),
            [], "",
        ))
    return entries


_ITEM_RE = re.compile(r"<item\b[^>]*>(.*?)</item>", re.S | re.I)


def _tag(block, name):
    m = re.search(r"<" + name + r"\b[^>]*>(.*?)</" + name + r">", block, re.S | re.I)
    if not m:
        return ""
    v = m.group(1).strip()
    if v.startswith("<![CDATA[") and v.endswith("]]>"):
        v = v[9:-3]
    return v


def _parse_regex(text):
    """名前空間の宣言漏れなど、壊れたXML向けのフォールバック。"""
    entries = []
    for block in _ITEM_RE.findall(text):
        cats = [c[9:-3] if c.startswith("<![CDATA[") else c for c in re.findall(r"<category\b[^>]*>(.*?)</category>", block, re.S)]
        entries.append(_entry(
            html.unescape(_tag(block, "title")), html.unescape(_tag(block, "link")),
            _tag(block, "pubDate") or _tag(block, "dc:date"),
            _tag(block, "description"), cats, _tag(block, "source"),
        ))
    return entries


def parse_feed(data):
    try:
        entries = _parse_etree(data)
    except ET.ParseError:
        entries = _parse_regex(data.decode("utf-8", errors="replace"))
    return [e for e in entries if e["title"] and e["url"]]
