import json
import os
from datetime import datetime

def load_articles():
    if os.path.exists('articles.json'):
        with open('articles.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def generate_html(articles):
    # ヘッダーとスタイル
    html = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>キャンプ・アウトドア最新情報まとめ</title>
<style>
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; background: #f8fafc; color: #1e293b; padding: 20px; margin: 0; line-height: 1.5; }
.container { max-width: 1000px; margin: 0 auto; }
.hero { width: 100%; height: 260px; border-radius: 12px; overflow: hidden; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); position: relative; }
.hero img { width: 100%; height: 100%; object-fit: cover; }
.hero-title { position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(transparent, rgba(0,0,0,0.75)); color: white; padding: 30px 20px 20px; font-size: 1.8rem; font-weight: bold; }
.filter-bar { display: flex; gap: 10px; margin-bottom: 30px; flex-wrap: wrap; justify-content: center; }
.filter-btn { background: #ffffff; border: 1px solid #cbd5e1; color: #475569; padding: 8px 18px; border-radius: 20px; font-weight: bold; cursor: pointer; transition: all 0.2s; font-size: 0.9rem; }
.filter-btn:hover { background: #e2e8f0; }
.filter-btn.active { background: #059669; color: white; border-color: #059669; box-shadow: 0 2px 4px rgba(5,150,105,0.2); }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
.card { background: white; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); display: flex; flex-direction: column; overflow: hidden; transition: transform 0.2s, box-shadow 0.2s; }
.card:hover { transform: translateY(-4px); box-shadow: 0 8px 15px rgba(0,0,0,0.1); }
.card-img { width: 100%; height: 170px; background: #e2e8f0; overflow: hidden; }
.card-img img { width: 100%; height: 100%; object-fit: cover; }
.card-content { padding: 18px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }
.title a { color: #1e293b; text-decoration: none; font-weight: bold; font-size: 1rem; line-height: 1.4; display: block; margin-bottom: 12px; }
.title a:hover { color: #059669; }
.meta { font-size: 0.8rem; color: #64748b; margin-bottom: 8px; display: flex; justify-content: space-between; }
.btn { color: #059669; font-weight: bold; text-decoration: none; font-size: 0.9rem; align-self: flex-start; display: inline-flex; align-items: center; gap: 4px; }
.btn:hover { text-decoration: underline; }
</style>
</head>
<body>
<div class="container">
<div class="hero">
<img src="https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?auto=format&fit=crop&w=1200&q=80" alt="キャンプ風景">
<div class="hero-title">🏕️ キャンプ・アウトドア情報まとめ</div>
</div>
<div class="filter-bar">
    <button class="filter-btn active" onclick="filterCards('all', this)">すべて</button>
</div>
<div class="grid">
"""
    
    # カード生成ループ
    for art in articles:
        img_url = art.get('image', 'https://images.unsplash.com/photo-1504280390367-361c6d9f38f4?auto=format&fit=crop&w=600&q=80')
        html += f"""
<div class="card">
    <div class="card-img"><img src="{img_url}" alt="記事画像" loading="lazy"></div>
    <div class="card-content">
        <div>
            <div class="meta"><span>{art.get('source', 'Web')}</span><span>{art.get('date', '')}</span></div>
            <div class="title"><a href="{art.get('url', '#')}" target="_blank">{art.get('title', '記事タイトル')}</a></div>
        </div>
        <a href="{art.get('url', '#')}" target="_blank" class="btn">記事を読む ➔</a>
    </div>
</div>
"""
    
    # フッターとスクリプト
    html += """
</div>
</div>
<script>
function filterCards(category, btn) {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.card').forEach(card => {
        card.style.display = (category === 'all' || card.dataset.time === category) ? 'flex' : 'none';
    });
}
</script>
</body>
</html>
"""
    return html

if __name__ == "__main__":
    articles = load_articles()
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(generate_html(articles))
