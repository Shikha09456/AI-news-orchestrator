# process_articles.py
import spacy
from dateparser import parse as dateparse
from sentence_transformers import SentenceTransformer
import numpy as np
from datetime import datetime
from typing import List, Dict
from config import EMBEDDING_MODEL
from tqdm import tqdm

import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import spacy.cli
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

embed_model = SentenceTransformer(EMBEDDING_MODEL)

def split_sentences(text):
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 20]

def extract_date_from_text(text):
    # Try to parse explicit date mentions in a sentence
    parsed = dateparse(text, settings={'PREFER_DATES_FROM': 'past'})
    if parsed:
        return parsed.date().isoformat()
    return None

def build_candidates(articles: List[Dict]):
    """
    For each article, split into sentences and mark any sentence with
    a date mention or event-word as a candidate.
    """
    candidates = []
    event_keywords = {"launch", "announce", "launched", "land", "landed", "release", "rolled out", "reported", "confirmed", "said", "claimed"}
    for art in articles:
        sentences = split_sentences(art.get("content", "") or art.get("raw_content", ""))
        for s in sentences:
            lower = s.lower()
            has_keyword = any(k in lower for k in event_keywords)
            date_mentioned = None
            # try spaCy entities for DATE as well
            doc = nlp(s)
            for ent in doc.ents:
                if ent.label_ == "DATE":
                    maybe = extract_date_from_text(ent.text)
                    if maybe:
                        date_mentioned = maybe
                        break
            # attempt parsing entire sentence if nothing found
            if not date_mentioned:
                date_mentioned = extract_date_from_text(s)
            if has_keyword or date_mentioned:
                candidates.append({
                    "article_url": art.get("url"),
                    "article_title": art.get("title"),
                    "article_source": art.get("source"),
                    "article_published": art.get("published_at"),
                    "sentence": s,
                    "date_mentioned": date_mentioned
                })
    # compute embeddings
    if candidates:
        sentences = [c["sentence"] for c in candidates]
        embeddings = embed_model.encode(sentences, show_progress_bar=True)
        for i, c in enumerate(candidates):
            c["embedding"] = embeddings[i].tolist()
    return candidates
