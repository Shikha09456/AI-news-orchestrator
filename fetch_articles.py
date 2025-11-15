# fetch_articles.py
# fetch_articles.py (robust extractor: tries newspaper3k if available, otherwise BeautifulSoup)
import requests
from bs4 import BeautifulSoup
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

def simple_text_from_html(url, timeout=8):
    """Fetch page HTML and heuristically extract text using BeautifulSoup."""
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Remove scripts/styles and common layout elements
        for tag in soup(["script", "style", "aside", "nav", "footer", "form", "header", "noscript"]):
            tag.decompose()

        # Prefer <article> or <main>
        main = soup.find("article") or soup.find("main")
        if main:
            paragraphs = main.find_all("p")
        else:
            paragraphs = soup.find_all("p")

        text_blocks = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
        text = "\n\n".join(text_blocks).strip()

        # Fallback to body text
        if not text:
            body = soup.body
            text = body.get_text(separator="\n", strip=True) if body else ""

        return text
    except Exception:
        return ""

def enrich_with_full_text(articles):
    enriched = []
    for a in articles:
        full_text = ""
        # Lazy import: attempt to use newspaper only if available
        try:
            from newspaper import Article  # import inside try so ImportError won't crash module import
            art = Article(a["url"])
            art.download()
            art.parse()
            full_text = art.text or ""
        except Exception:
            # Fallback to BeautifulSoup extraction (no compiled lxml dependency)
            full_text = simple_text_from_html(a["url"]) or a.get("raw_content") or ""

        enriched.append({
            **a,
            "content": full_text,
        })
        # be polite to remote servers
        time.sleep(0.1)
    return enriched

def fetch_articles(query, limit=MAX_ARTICLES):
    raw = fetch_from_newsapi(query, page_size=limit)
    return enrich_with_full_text(raw)

if __name__ == "__main__":
    q = "OpenAI GPT-5 Launch"
    arts = fetch_articles(q)
    print(f"Fetched {len(arts)} articles")
    for a in arts[:3]:
        print(a["title"], a["source"], a["published_at"])
