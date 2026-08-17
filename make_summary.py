import json
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup

def scrape_camp_news():
    articles = []
    try:
        if os.path.exists('articles.json'):
            with open('articles.json', 'r', encoding='utf-8') as f:
                articles = json.load(f)
    except Exception as e:
        print(f"Error loading articles: {e}")
    return articles

def generate_html(articles):
    html_content = """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>キャンプニュース</title>
    <style>
        body { font-family: sans-serif; background-color: #f4f7f6; margin: 0; padding: 15px; color: #333; }
        h1 { text-align: center; color: #2c3e50; }
        .card-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; max-width: 1000px; margin: 0 auto; }
        .card { background: white; border-radius: 12px; padding: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: transform 0.2s; }
        .card:hover { transform: translateY(-5px); }
        .card a { text-decoration: none; color: #333; }
        .card h3 { margin: 0 0 10px 0; font-size: 1.1rem; line-height: 1.4; }
        .card p { font-size: 0.85rem; color: #666; margin: 0; }
        @media (max-width: 600px) { .card-container { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <h1>🏕️ キャンプニュース</h1>
    <div class="card-container">
"""
    for article in articles:
        title = article.get("title", "タイトルなし")
        url = article.get("url", "#")
        date = article.get("date", "")
        source = article.get("source", "")
        if url != "#":
            html_content += f"""<div class="card"><a href="{url}" target="_blank"><h3>{title}</h3><p>🕒 {date} | 🌐 {source}</p></a></div>"""
        else:
            html_content += f"""<div class="card"><h3>{title}</h3><p>🕒 {date} | 🌐 {source}</p></div>"""
    html_content += "</div></body></html>"
    return html_content

if __name__ == "__main__":
    articles = scrape_camp_news()
    if not articles:
        articles = [{
            "title": "キャンプニュースダッシュボードへようこそ！",
            "url": "https://mametru.github.io/camp-news/",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "System"
        }]
    
    with open("articles.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
        
    html_out = generate_html(articles)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_out)
    print("Successfully generated index.html and articles.json")
