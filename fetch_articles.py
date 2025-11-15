# fetch_articles.py
import requests
from newspaper import Article
from datetime import datetime
from config import NEWSAPI_KEY, MAX_ARTICLES
import time

NEWSAPI_URL = "https://newsapi.org/v2/everything"

def fetch_from_newsapi(query, page_size=MAX_ARTICLES):
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "apiKey": NEWSAPI_KEY
    }
    resp = requests.get(NEWSAPI_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    articles = []
    for item in data.get("articles", []):
        url = item.get("url")
        published_at = item.get("publishedAt")
        articles.append({
            "title": item.get("title"),
            "url": url,
            "published_at": published_at,
            "source": item.get("source", {}).get("name"),
            "raw_content": item.get("content") or ""
        })
    return articles

def enrich_with_full_text(articles, max_wait=1.0):
    enriched = []
    for a in articles:
        full_text = ""
        try:
            art = Article(a["url"])
            art.download()
            art.parse()
            full_text = art.text
        except Exception:
            full_text = a.get("raw_content") or ""
        enriched.append({
            **a,
            "content": full_text,
        })
        time.sleep(0.1)  # be polite
    return enriched

def fetch_articles(query, limit=MAX_ARTICLES):
    raw = fetch_from_newsapi(query, page_size=limit)
    return enrich_with_full_text(raw, max_wait=1.0)

if __name__ == "__main__":
    q = "OpenAI GPT-5 Launch"
    arts = fetch_articles(q)
    print(f"Fetched {len(arts)} articles")
    for a in arts[:3]:
        print(a["title"], a["source"], a["published_at"])
