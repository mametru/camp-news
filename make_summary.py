import requests
from bs4 import BeautifulSoup
import json
import datetime

# --- ここにスクレイピング処理など、あなたの既存のコードが入ります ---
# (既存のコードが長いため、この部分は元のスクリプトからコピーしてください)
# 今回はデザイン更新のみに集中するため、HTML生成部分のみを以下のように定義します

def generate_html(articles):
    html_content = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>キャンプニュース</title>
    <style>
        body { font-family: sans-serif; background-color: #f4f7f6; margin: 0; padding: 15px; color: #333; }
        h1 { text-align: center; color: #2c3e50; }
        .card-container { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); 
            gap: 15px; 
            max-width: 1000px; 
            margin: 0 auto; 
        }
        .card { 
            background: white; 
            border-radius: 12px; 
            padding: 16px; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1); 
            transition: transform 0.2s;
        }
        .card:hover { transform: translateY(-5px); }
        .card a { text-decoration: none; color: #333; }
        .card h3 { margin: 0 0 10px 0; font-size: 1.1rem; line-height: 1.4; }
        .card p { font-size: 0.85rem; color: #666; margin: 0; }
        @media (max-width: 600px) {
            .card-container { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <h1>🏕️ キャンプニュース</h1>
    <div class="card-container">
"""
    for article in articles:
        html_content += f"""
        <div class="card">
            <a href="{article['url']}" target="_blank">
                <h3>{article['title']}</h3>
                <p>🕒 {article['date']} | 🌐 {article['source']}</p>
            </a>
        </div>
    """
    html_content += "</div></body></html>"
    return html_content

# --- ここから下は、既存の処理と呼び出しを繋いでください ---
# 例: 
# articles = scrape_news()
# with open("index.html", "w", encoding="utf-8") as f:
#     f.write(generate_html(articles))
