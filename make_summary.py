import requests
from bs4 import BeautifulSoup
import email.utils
from datetime import datetime, timedelta, timezone
import json
import os
import urllib.parse

DATA_FILE = "articles.json"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

# 現在時刻（JST）
now_jst = datetime.now(timezone(timedelta(hours=9)))

# 除外したいキーワード
exclude_keywords = ['プロ野球', '野球', '春季キャンプ', '学校', '生徒', '中学', '高校', '子供', '子ども', '英語', '英会話', '留学', 'キッズ']

def is_valid_camp_article(title):
    if 'キャンプ' not in title and 'アウトドア' not in title and 'ギア' not in title:
        return False
    for word in exclude_keywords:
        if word in title:
            return False
    return True

def classify_time(dt):
    if not dt:
        return 'old', '日時不明'
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=9)))
    else:
        dt = dt.astimezone(timezone(timedelta(hours=9)))
        
    diff = now_jst - dt
    date_str = dt.strftime("%Y/%m/%d %H:%M")
    
    if diff <= timedelta(days=1):
        return '1day', date_str
    elif diff <= timedelta(days=3):
        return '3days', date_str
    elif diff <= timedelta(days=7):
        return '1week', date_str
    else:
        return 'old', date_str

def fetch_article_details(url):
    default_img = "https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?auto=format&fit=crop&w=600&q=80"
    img_url = default_img
    dt_obj = None
    try:
        res = requests.get(url, headers=headers, timeout=3, allow_redirects=True)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            og_img = soup.find('meta', property='og:image')
            if og_img and og_img.get('content'):
                img_url = og_img['content']
            
            time_tag = soup.find('time')
            if time_tag and time_tag.has_attr('datetime'):
                try:
                    dt_obj = datetime.fromisoformat(time_tag['datetime'].replace('Z', '+00:00'))
                except:
                    pass
    except:
        pass
    return img_url, dt_obj

# 1. 既存蓄積データの読み込み
all_articles = []
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            all_articles = json.load(f)
        print(f"過去の蓄積データ {len(all_articles)} 件を読み込みました。")
    except:
        all_articles = []

existing_links = {art['link'] for art in all_articles}
new_count = 0

print("専門メディア、メーカー、ニュースサイトからキャンプ情報を総収集中（画像も取得中）...")

search_queries = [
    "キャンプ",
    "CAMP HACK",
    "BE-PAL キャンプ",
    "LANTERN キャンプ",
    "スノーピーク 新製品",
    "コールマン キャンプギア",
    "DOD キャンプ",
    "SOTO バーナー",
    "アウトドアギア PR TIMES"
]

# --- A. Googleニュース ---
for query in search_queries:
    encoded_q = urllib.parse.quote(query)
    g_url = f"https://news.google.com/rss/search?q={encoded_q}&hl=ja&gl=JP&ceid=JP:ja"
    try:
        res_g = requests.get(g_url, headers=headers, timeout=5)
        if res_g.status_code == 200:
            soup_g = BeautifulSoup(res_g.content, 'xml')
            items = soup_g.find_all('item')
            for item in items[:8]:
                title = item.find('title').text if item.find('title') else ""
                link = item.find('link').text if item.find('link') else "#"
                pubDate_str = item.find('pubDate').text if item.find('pubDate') else ""
                source = item.find('source').text if item.find('source') else "アウトドア速報"
                
                if title and is_valid_camp_article(title):
                    if link not in existing_links:
                        img_url, dt_obj = fetch_article_details(link)
                        
                        if not dt_obj and pubDate_str:
                            try:
                                dt_obj = email.utils.parsedate_to_datetime(pubDate_str)
                            except:
                                pass
                            
                        time_class, date_str = classify_time(dt_obj)
                        
                        new_art = {
                            'title': title,
                            'link': link,
                            'image': img_url,
                            'source': source,
                            'date': date_str,
                            'time_class': time_class
                        }
                        all_articles.insert(0, new_art)
                        existing_links.add(link)
                        new_count += 1
    except:
        pass

# --- B. Yahoo!ニュース ---
y_url = "https://news.yahoo.co.jp/search?p=%E3%82%AD%E3%83%A3%E3%83%B3%E3%83%97"
try:
    res_y = requests.get(y_url, headers=headers, timeout=5)
    if res_y.status_code == 200:
        soup_y = BeautifulSoup(res_y.text, 'html.parser')
        for a_tag in soup_y.find_all('a', href=True):
            href = a_tag['href']
            if 'news.yahoo.co.jp/articles/' in href:
                title = a_tag.get_text().strip()
                if title and is_valid_camp_article(title):
                    if href not in existing_links:
                        img_url, dt_obj = fetch_article_details(href)
                        time_class, date_str = classify_time(dt_obj)
                        
                        new_art = {
                            'title': title,
                            'link': href,
                            'image': img_url,
                            'source': 'Yahoo!ニュース',
                            'date': date_str,
                            'time_class': time_class
                        }
                        all_articles.insert(0, new_art)
                        existing_links.add(href)
                        new_count += 1
except:
    pass

print(f"新規に {new_count} 件の記事を追加しました！（累計ストック: {len(all_articles)} 件）")

with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(all_articles, f, ensure_ascii=False, indent=2)

total_count = len(all_articles)

html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-D9MG4MRBB5"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());

  gtag('config', 'G-D9MG4MRBB5');
</script>
<meta name="google-site-verification" content="hBCTAgRhB0rpRLp1YYaR5p2yKLzPOer32cFWVVPL1rI" />
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>キャンプ・アウトドア最新情報まとめ</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background: #f8fafc; color: #1e293b; padding: 20px; margin: 0; line-height: 1.5; }}
.container {{ max-width: 1000px; margin: 0 auto; }}
.hero {{ width: 100%; height: 260px; border-radius: 12px; overflow: hidden; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); position: relative; }}
.hero img {{ width: 100%; height: 100%; object-fit: cover; }}
.hero-title {{ position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(transparent, rgba(0,0,0,0.75)); color: white; padding: 30px 20px 20px; font-size: 1.8rem; font-weight: bold; }}

.filter-bar {{ display: flex; gap: 10px; margin-bottom: 30px; flex-wrap: wrap; justify-content: center; }}
.filter-btn {{ background: #ffffff; border: 1px solid #cbd5e1; color: #475569; padding: 8px 18px; border-radius: 20px; font-weight: bold; cursor: pointer; transition: all 0.2s; font-size: 0.9rem; }}
.filter-btn:hover {{ background: #e2e8f0; }}
.filter-btn.active {{ background: #059669; color: white; border-color: #059669; box-shadow: 0 2px 4px rgba(5,150,105,0.2); }}

.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
.card {{ background: white; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); display: flex; flex-direction: column; overflow: hidden; transition: transform 0.2s, box-shadow 0.2s; }}
.card:hover {{ transform: translateY(-4px); box-shadow: 0 8px 15px rgba(0,0,0,0.1); }}
.card-img {{ width: 100%; height: 170px; background: #e2e8f0; overflow: hidden; }}
.card-img img {{ width: 100%; height: 100%; object-fit: cover; }}
.card-content {{ padding: 18px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }}
.title a {{ color: #1e293b; text-decoration: none; font-weight: bold; font-size: 1rem; line-height: 1.4; display: block; margin-bottom: 12px; }}
.title a:hover {{ color: #059669; }}
.meta {{ font-size: 0.8rem; color: #64748b; margin-bottom: 8px; display: flex; justify-content: space-between; }}
.btn {{ color: #059669; font-weight: bold; text-decoration: none; font-size: 0.9rem; align-self: flex-start; display: inline-flex; align-items: center; gap: 4px; }}
.btn:hover {{ text-decoration: underline; }}

/* --- スマホ向けレスポンシブ調整 --- */
@media (max-width: 600px) {{
    body {{ padding: 10px; }}
    .hero {{ height: 180px; margin-bottom: 15px; }}
    .hero-title {{ font-size: 1.2rem; padding: 20px 15px 15px; }}
    .filter-bar {{ gap: 6px; margin-bottom: 20px; }}
    .filter-btn {{ padding: 6px 12px; font-size: 0.8rem; }}
    .grid {{ grid-template-columns: 1fr; gap: 15px; }}
    .card-content {{ padding: 14px; }}
}}
</style>
</head>
<body>
<div class="container">
<div class="hero">
<img src="https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?auto=format&fit=crop&w=1200&q=80" alt="キャンプ風景">
<div class="hero-title">🏕️ キャンプ・アウトドア情報まとめ</div>
</div>

<div class="filter-bar">
    <button class="filter-btn active" onclick="filterCards('all', this)">すべて ({total_count})</button>
    <button class="filter-btn" onclick="filterCards('1day', this)">1日前</button>
    <button class="filter-btn" onclick="filterCards('3days', this)">3日前</button>
    <button class="filter-btn" onclick="filterCards('1week', this)">1週間前</button>
</div>

<div class="grid">"""

for art in all_articles:
    time_val = art.get('time_class', 'old')
    html_content += f"""
<div class="card" data-time="{time_val}">
<div class="card-img">
<img src="{art['image']}" alt="記事画像" loading="lazy">
</div>
<div class="card-content">
<div>
<div class="meta"><span>{art['source']}</span><span>{art['date']}</span></div>
<div class="title"><a href="{art['link']}" target="_blank">{art['title']}</a></div>
</div>
<a href="{art['link']}" target="_blank" class="btn">記事を読む ➔</a>
</div>
</div>"""

html_content += """
</div>
</div>

<script>
function filterCards(category, btn) {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    document.querySelectorAll('.card').forEach(card => {
        if (category === 'all' || card.dataset.time === category) {
            card.style.display = 'flex';
        } else {
            card.style.display = 'none';
        }
    });
}
</script>
</body>
</html>"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_content)
    
print("✨ Googleサーチコンソール確認用タグの埋め込みが完了しました！")
