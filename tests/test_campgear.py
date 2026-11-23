import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from campgear import affiliate, render, store  # noqa: E402
from campgear.classify import classify, clean_title, detect_brand, detect_category  # noqa: E402
from campgear.fetch import parse_feed, safe_url  # noqa: E402

CFG = {
    "site": {"name": "テスト", "tagline": "t", "base_url": "https://example.com/", "contact_url": ""},
    "analytics": {"ga4_measurement_id": "G-TEST123"},
    "affiliate": {"amazon_tag": "", "rakuten_affiliate_id": ""},
}
VERSIONS = {"style": "1", "app": "1", "analytics": "1"}


def make_item(**kw):
    base = {
        "id": "abc", "title": "スノーピーク 新作テント発売", "url": "https://example.com/a", "summary": "",
        "source": "PR TIMES", "source_id": "prtimes", "kind": "new", "brand": "スノーピーク",
        "category": "tent", "published": "2026-11-20T00:00:00Z", "first_seen": "2026-11-20T00:00:00Z",
    }
    base.update(kw)
    return base


class ClassifyTest(unittest.TestCase):
    def test_new_product(self):
        v = classify("スノーピーク、全方向から炎を楽しめる薪ストーブを発売")
        self.assertEqual(v, {"kind": "new", "brand": "スノーピーク", "category": "heater"})

    def test_sale(self):
        v = classify("【最大52％OFF】ポータブル電源のJackery、ブラックフライデーセールを開催！")
        self.assertEqual(v["kind"], "sale")
        self.assertEqual(v["brand"], "Jackery")
        self.assertEqual(v["category"], "power")

    def test_black_friday_is_not_rack(self):
        self.assertEqual(detect_category("Amazon ブラックフライデー開催"), "other")

    def test_excluded(self):
        self.assertIsNone(classify("プロ野球春季キャンプ 新ユニフォーム発売"))
        self.assertIsNone(classify("キャンプ・シュワブで新施設が登場"))

    def test_irrelevant(self):
        self.assertIsNone(classify("新型スマートフォン発売"))

    def test_not_product_news(self):
        self.assertIsNone(classify("週末はキャンプへ行こう"))

    def test_ascii_brand_boundary(self):
        self.assertEqual(detect_brand("DODの新作テント"), "DOD")
        self.assertEqual(detect_brand("GOODOGの記事"), "")

    def test_clean_title(self):
        self.assertEqual(clean_title("画像2 / 27＞ロゴスの新作 - ウォーカープラス", "ウォーカープラス"), "ロゴスの新作")
        self.assertEqual(clean_title("薪ストーブを発売 | 株式会社スノーピークのプレスリリース"), "薪ストーブを発売")


class FeedTest(unittest.TestCase):
    def test_rss2(self):
        xml = b"""<?xml version="1.0"?><rss><channel><item><title>A &amp; B</title><link>https://x.example/1</link>
        <pubDate>Mon, 23 Nov 2026 09:00:00 +0000</pubDate><description>&lt;p&gt;hello&lt;/p&gt;</description>
        <category>c1</category></item><item><title>bad</title><link>javascript:alert(1)</link></item></channel></rss>"""
        entries = parse_feed(xml)
        self.assertEqual(len(entries), 1)  # javascript: リンクは除外
        self.assertEqual(entries[0]["title"], "A & B")
        self.assertEqual(entries[0]["summary"], "hello")
        self.assertEqual(entries[0]["published"], datetime(2026, 11, 23, 9, tzinfo=timezone.utc))

    def test_broken_xml_fallback(self):
        xml = b"""<rss><channel><item><title><![CDATA[T1]]></title><link>https://x.example/1</link>
        <foo:bar>unbound</foo:bar></item></channel></rss>"""
        entries = parse_feed(xml)
        self.assertEqual([e["title"] for e in entries], ["T1"])

    def test_control_chars_removed(self):
        xml = "<rss><channel><item><title>A\x01B</title><link>https://x.example/1</link></item></channel></rss>"
        self.assertEqual(parse_feed(xml.encode())[0]["title"], "AB")

    def test_rss_output_is_valid_xml(self):
        import xml.etree.ElementTree as ET
        ET.fromstring(render.rss(CFG, [make_item(title="<b>&\"'", summary="x")], "2026-11-23T00:00:00Z").encode())

    def test_safe_url(self):
        self.assertEqual(safe_url("https://a.example/x"), "https://a.example/x")
        self.assertEqual(safe_url("javascript:alert(1)"), "")
        self.assertEqual(safe_url("//a.example"), "")


class StoreTest(unittest.TestCase):
    def test_merge_dedupe_and_prune(self):
        now = datetime(2026, 11, 23, tzinfo=timezone.utc)
        old = make_item(id="old", title="古い記事 発売", published=store.iso(now - timedelta(days=100)))
        a = make_item(id="a", title="EcoFlowがブラックフライデーセール、新型も値下げ")
        dup = make_item(id="b", title="EcoFlowがブラックフライデーセール、新型も値下げ (2026年11月21日掲載)")
        items, added = store.merge([old], [a, dup], now, max_age_days=90, max_items=10)
        self.assertEqual([i["id"] for i in items], ["a"])
        self.assertEqual(added, 1)

    def test_canonical_url_strips_tracking(self):
        self.assertEqual(store.item_id("https://A.example/x?utm_source=z&id=1"), store.item_id("https://a.example/x?id=1"))


class RenderTest(unittest.TestCase):
    def test_xss_is_escaped(self):
        evil = make_item(title='<script>alert(1)</script>"><img onerror=x>', source='"><b>', brand='x"y')
        html = render.card(evil, CFG, "")
        self.assertNotIn("<script>alert", html)
        self.assertNotIn('"><img', html)
        self.assertNotIn('"><b>', html)
        self.assertIn("&lt;script&gt;", html)

    def test_unsafe_url_card_dropped(self):
        self.assertEqual(render.card(make_item(url="javascript:alert(1)"), CFG, ""), "")

    def test_page_has_ga_and_csp(self):
        page = render.listing_page(CFG, [make_item()], [make_item()], "2026-11-23T00:00:00Z", VERSIONS)
        self.assertIn("gtag/js?id=G-TEST123", page)
        self.assertIn("Content-Security-Policy", page)
        self.assertNotIn("<script>\n", page)  # インラインスクリプトなし

    def test_affiliate_hidden_without_ids(self):
        self.assertEqual(affiliate.links_for_item(make_item(), CFG["affiliate"]), [])
        self.assertNotIn("aff-btn", render.card(make_item(), CFG, ""))

    def test_affiliate_links_with_ids(self):
        cfg = {"amazon_tag": "mytag-22", "rakuten_affiliate_id": "1a2b.3c4d"}
        links = affiliate.links_for_item(make_item(), cfg)
        self.assertEqual([s for s, _, _ in links], ["amazon", "rakuten"])
        self.assertIn("tag=mytag-22", links[0][2])
        full = dict(CFG, affiliate=cfg)
        html = render.card(make_item(), full, "")
        self.assertIn('rel="sponsored noopener"', html)
        self.assertIn("PR", html)

    def test_invalid_affiliate_id_ignored(self):
        cfg = {"amazon_tag": 'x"><script>', "rakuten_affiliate_id": ""}
        self.assertEqual(affiliate.links_for_item(make_item(), cfg), [])


if __name__ == "__main__":
    unittest.main()
