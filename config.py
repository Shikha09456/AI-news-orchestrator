# config.py
# Put your keys here or set environment variables and fallback to them.
import os

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "7bb1c3ac61e94ff6b27ffd60da1987ef")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "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")

# Optional tuning
MAX_ARTICLES = 12
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "gpt-5"   # update if you use a different name
