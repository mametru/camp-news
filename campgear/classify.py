"""記事の判定・分類（キャンプ関連か / 新製品かセールか / ブランド / カテゴリ）。"""
import re
import unicodedata

# (表示名, [別名...])。英字の別名は大文字小文字を無視し、英数字の境界で一致判定する。
BRANDS = [
    ("スノーピーク", ["スノーピーク", "snow peak", "snowpeak"]),
    ("コールマン", ["コールマン", "coleman"]),
    ("DOD", ["DOD", "ディーオーディー", "ドッペルギャンガー"]),
    ("ogawa", ["ogawa", "オガワ"]),
    ("ロゴス", ["ロゴス", "logos"]),
    ("キャプテンスタッグ", ["キャプテンスタッグ", "captain stag"]),
    ("モンベル", ["モンベル", "mont-bell", "montbell"]),
    ("SOTO", ["SOTO", "新富士バーナー"]),
    ("イワタニ", ["イワタニ", "岩谷産業", "iwatani"]),
    ("ユニフレーム", ["ユニフレーム", "uniflame"]),
    ("テンマクデザイン", ["テンマクデザイン", "tent-mark designs", "tent-mark"]),
    ("ヘリノックス", ["ヘリノックス", "helinox"]),
    ("ノルディスク", ["ノルディスク", "nordisk"]),
    ("ザ・ノース・フェイス", ["ノースフェイス", "ノース・フェイス", "north face"]),
    ("パタゴニア", ["パタゴニア", "patagonia"]),
    ("ワークマン", ["ワークマン", "workman"]),
    ("Jackery", ["jackery", "ジャクリ"]),
    ("EcoFlow", ["ecoflow", "エコフロー"]),
    ("Anker", ["anker", "アンカー"]),
    ("BLUETTI", ["bluetti", "ブルーティ"]),
    ("YETI", ["YETI", "イエティ"]),
    ("スタンレー", ["スタンレー", "stanley"]),
    ("ペトロマックス", ["ペトロマックス", "petromax"]),
    ("ベアボーンズ", ["ベアボーンズ", "barebones"]),
    ("ゼインアーツ", ["ゼインアーツ", "zane arts"]),
    ("サバティカル", ["サバティカル", "sabbatical"]),
    ("Naturehike", ["naturehike", "ネイチャーハイク"]),
    ("バンドック", ["バンドック", "bundok"]),
    ("MSR", ["MSR"]),
    ("プリムス", ["プリムス", "primus"]),
    ("ジェットボイル", ["ジェットボイル", "jetboil"]),
    ("ナンガ", ["ナンガ", "nanga"]),
    ("イスカ", ["イスカ", "isuka"]),
    ("グラナイトギア", ["グラナイトギア", "granite gear"]),
    ("ミレー", ["ミレー", "millet"]),
    ("カリマー", ["カリマー", "karrimor"]),
    ("トランギア", ["トランギア", "trangia"]),
    ("ゴールゼロ", ["ゴールゼロ", "goal zero", "goalzero"]),
    ("ベルモント", ["ベルモント", "belmont"]),
    ("村の鍛冶屋", ["村の鍛冶屋"]),
    ("フィールドア", ["フィールドア", "fieldoor"]),
    ("クイックキャンプ", ["クイックキャンプ", "quickcamp"]),
    ("ニトリ", ["ニトリ"]),
    ("無印良品", ["無印良品"]),
    ("Hilander", ["hilander", "ハイランダー"]),
]

# (slug, 表示名, アイコン, [キーワード...])。上から順に最初に一致したものを採用。
CATEGORIES = [
    ("power", "ポータブル電源", "🔋", ["ポータブル電源", "ポータブルバッテリー", "ソーラーパネル", "蓄電池"]),
    ("heater", "暖房・ストーブ", "🔥", ["石油ストーブ", "薪ストーブ", "ガスストーブ", "ヒーター", "電気毛布", "湯たんぽ"]),
    ("tent", "テント・タープ", "⛺", ["テント", "タープ", "シェルター", "ツールーム", "ワンポール", "スクリーン"]),
    ("sleep", "寝袋・マット・コット", "🛏️", ["寝袋", "シュラフ", "スリーピングバッグ", "マット", "コット", "枕", "ハンモック"]),
    ("furniture", "チェア・テーブル", "🪑", ["チェア", "テーブル", "ベンチ", "シェルフ", "ギアラック", "ワゴン", "キャリーカート"]),
    ("light", "ランタン・ライト", "🏮", ["ランタン", "ライト", "ランプ", "ヘッドランプ"]),
    ("fire", "焚き火・BBQ", "🪵", ["焚き火", "焚火", "たき火", "薪", "グリル", "bbq", "バーベキュー", "ファイアピット", "炭"]),
    ("cook", "調理・クッカー", "🍳", ["クッカー", "バーナー", "コンロ", "シングルバーナー", "ダッチオーブン", "スキレット", "ケトル", "メスティン", "ホットサンド", "鍋", "フライパン", "ガス缶"]),
    ("cooler", "クーラー・ボトル", "🧊", ["クーラーボックス", "クーラーバッグ", "保冷", "ボトル", "タンブラー", "ジャグ", "水筒"]),
    ("bag", "バッグ・リュック", "🎒", ["バックパック", "ザック", "リュック", "バッグ", "コンテナ", "収納"]),
    ("wear", "ウェア・シューズ", "🧥", ["ジャケット", "フリース", "ダウン", "ウェア", "シューズ", "ブーツ", "パンツ", "グローブ", "アパレル"]),
]
OTHER_CATEGORY = ("other", "その他ギア", "🏕️")
CATEGORY_BY_SLUG = {c[0]: c for c in CATEGORIES}
CATEGORY_BY_SLUG[OTHER_CATEGORY[0]] = (*OTHER_CATEGORY, [])

# キャンプ関連と判断する語（ブランド一致でも可）
RELEVANT_WORDS = [
    "キャンプ", "アウトドア", "グランピング", "ソロキャン", "ギア", "登山", "ハイキング", "トレッキング",
    "テント", "タープ", "寝袋", "シュラフ", "ランタン", "焚き火", "焚火", "バーナー", "クッカー",
    "コット", "ポータブル電源", "クーラーボックス", "バーベキュー", "bbq", "車中泊",
]

# 明らかに無関係な記事を除外
EXCLUDE_WORDS = [
    "プロ野球", "野球", "春季キャンプ", "秋季キャンプ", "春季", "キャンプ・シュワブ", "キャンプシュワブ",
    "キャンプ・ハンセン", "キャンプ座間", "米軍", "サッカー", "jリーグ", "代表合宿", "合宿", "留学",
    "英会話", "英語キャンプ", "求人", "採用", "決算", "株価", "業績", "逮捕", "事故", "死亡", "遭難",
    "火災", "クマ被害", "クマ出没", "ブートキャンプ", "ゲーム", "アニメ", "ガチャ", "映画", "ドラマ",
]

SALE_WORDS = [
    "セール", "sale", "割引", "値下げ", "特価", "半額", "クーポン", "アウトレット",
    "ブラックフライデー", "black friday", "サイバーマンデー", "プライムデー", "タイムセール",
    "福袋", "初売り", "ポイント還元", "最安", "キャンペーン",
]

NEW_WORDS = [
    "新製品", "新作", "新商品", "新発売", "発売", "新登場", "登場", "新色", "新モデル", "リニューアル",
    "予約開始", "先行販売", "限定", "コラボ", "受注", "ローンチ", "デビュー", "販売開始", "新ライン",
]

# 「52%OFF」「最大30%」「1000円オフ」など
_SALE_RE = re.compile(r"\d+\s*%\s*(off|オフ|引)|最大\s*\d+\s*%|\d+\s*円\s*(off|オフ|引)")
_ASCII_ALIAS = re.compile(r"^[a-z0-9 .\-]+$")


def normalize(text):
    """全角/半角・大小文字の揺れを吸収した比較用文字列。"""
    return unicodedata.normalize("NFKC", text or "").lower()


def _contains_any(norm_text, words):
    return any(normalize(w) in norm_text for w in words)


def _alias_pattern(alias):
    a = normalize(alias)
    if _ASCII_ALIAS.match(a):
        return re.compile(r"(?<![a-z0-9])" + re.escape(a) + r"(?![a-z0-9])")
    return re.compile(re.escape(a))


_BRAND_PATTERNS = [(name, [_alias_pattern(a) for a in aliases]) for name, aliases in BRANDS]


def detect_brand(text):
    norm = normalize(text)
    for name, patterns in _BRAND_PATTERNS:
        if any(p.search(norm) for p in patterns):
            return name
    return ""


def detect_category(text):
    norm = normalize(text)
    for slug, _label, _icon, words in CATEGORIES:
        if _contains_any(norm, words):
            return slug
    return OTHER_CATEGORY[0]


def detect_kind(title, extra="", trusted_new=False):
    """'sale' / 'new' / '' (対象外)。セール判定はタイトル優先。"""
    t = normalize(title)
    if _contains_any(t, SALE_WORDS) or _SALE_RE.search(t):
        return "sale"
    if trusted_new or _contains_any(t, NEW_WORDS):
        return "new"
    e = normalize(extra)
    if _contains_any(e, SALE_WORDS):
        return "sale"
    if _contains_any(e, NEW_WORDS):
        return "new"
    return ""


def is_relevant(title, extra="", brand=""):
    t = normalize(title)
    if _contains_any(t, EXCLUDE_WORDS):
        return False
    if brand:
        return True
    return _contains_any(t, RELEVANT_WORDS) or _contains_any(normalize(extra), RELEVANT_WORDS[:6])


_TITLE_NOISE = [
    re.compile(r"^画像\s*\d+\s*/\s*\d+\s*[＞>]\s*"),        # 「画像2 / 27＞」
    re.compile(r"\s+-\s+エキスパート$"),                      # Yahoo!エキスパート
    re.compile(r"\s*[|｜]\s*[^|｜]*のプレスリリース$"),          # PR TIMES
    re.compile(r"\s*[(（]\d{4}年\d{1,2}月\d{1,2}日掲載[)）]$"),  # ライブドア等
]


def clean_title(title, source_name=""):
    """余分な空白・Googleニュースの「 - 媒体名」末尾を除去。"""
    t = re.sub(r"\s+", " ", (title or "")).strip()
    if source_name and t.endswith(" - " + source_name):
        t = t[: -len(" - " + source_name)].rstrip()
    for pattern in _TITLE_NOISE:
        t = pattern.sub("", t).strip()
    return t[:200]


def classify(title, summary="", trusted_new=False):
    """記事を判定し、対象外なら None を返す。"""
    brand = detect_brand(title) or detect_brand(summary[:200])
    if not is_relevant(title, summary, brand):
        return None
    kind = detect_kind(title, summary[:200], trusted_new)
    if not kind:
        return None
    category = detect_category(title)
    if category == OTHER_CATEGORY[0]:
        category = detect_category(summary[:200])
    return {"kind": kind, "brand": brand, "category": category}
