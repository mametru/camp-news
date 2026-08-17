import requests
from bs4 import BeautifulSoup

url = "https://ja.wikipedia.org/wiki/キャンプ"

# ここがポイント！「私はChromeブラウザです」という身分証明書を作る
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# headersを付けて（身分証明書を見せながら）アクセスする
response = requests.get(url, headers=headers)

if response.status_code == 200:
    print("通信成功！データを取得しました。")
    soup = BeautifulSoup(response.text, 'html.parser')
    
    print("==============================")
    print("ページのタイトル:", soup.title.text)
    print("==============================")
else:
    print("通信に失敗しました。エラーコード:", response.status_code)
