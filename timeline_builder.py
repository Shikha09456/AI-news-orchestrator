# timeline_builder.py
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from collections import defaultdict, Counter
import openai
import json
from config import OPENAI_API_KEY, LLM_MODEL
from dateutil.parser import parse as parse_dt

openai.api_key = OPENAI_API_KEY

def cluster_candidates(candidates, distance_threshold=1.05):
    """
    Agglomerative clustering over embeddings.
    Adjust distance_threshold for coarser/finer clusters.
    """
    if not candidates:
        return []
    X = np.array([c["embedding"] for c in candidates])
    # choose n_clusters by heuristic: allow clustering by distance threshold
    clustering = AgglomerativeClustering(n_clusters=None, distance_threshold=distance_threshold, linkage="average")
    labels = clustering.fit_predict(X)
    clustered = defaultdict(list)
    for lab, c in zip(labels, candidates):
        clustered[int(lab)].append(c)
    clusters = list(clustered.values())
    return clusters

def canonical_date_for_cluster(cluster):
    # gather explicit dates mentioned then fallback to article publish dates
    dates = []
    weights = []
    for item in cluster:
        if item.get("date_mentioned"):
            try:
                d = parse_dt(item["date_mentioned"]).date()
                dates.append(d)
                weights.append(1.5)  # date mention gets higher weight
            except Exception:
                pass
        # fallback to article publish date
        try:
            pub = item.get("article_published")
            if pub:
                dpub = parse_dt(pub).date()
                dates.append(dpub)
                weights.append(1.0)
        except Exception:
            pass
    if not dates:
        return None
    # compute weighted median by converting to ordinal
    ordinals = [d.toordinal() for d in dates]
    # weighted median
    sorted_pairs = sorted(zip(ordinals, weights))
    total_w = sum(weights)
    cumulative = 0
    for o, w in sorted_pairs:
        cumulative += w
        if cumulative >= total_w / 2:
            return datetime_from_ordinal(o)
    # fallback
    return datetime_from_ordinal(ordinals[int(len(ordinals)/2)])

def datetime_from_ordinal(ordv):
    from datetime import date
    d = date.fromordinal(int(ordv))
    return d.isoformat()

def summarize_cluster_with_llm(cluster, candidate_date):
    """
    Call LLM to create a short milestone sentence and confidence.
    Prompt contains only supporting quotes and provenance to reduce halluc.
    """
    # Prepare prompt
    supports = []
    for c in cluster:
        supports.append(f"- ({c['article_source']}) \"{c['sentence']}\" (url: {c['article_url']})")
    prompt = (
        "You are a factual summarizer. Given the supporting sentences from news articles below, "
        "produce:\n1) ONE short canonical milestone sentence (10-25 words) strictly based on the supporting quotes.\n"
        "2) a confidence score (0-1) indicating how well supported it is.\n3) list up to 3 sources that best support the milestone.\n"
        "If the supporting quotes contradict each other, indicate 'CONTRADICTION DETECTED' and list the differing claims.\n\n"
        f"Candidate canonical date: {candidate_date}\n\nSupporting quotes:\n" + "\n".join(supports) + "\n\nRespond in JSON with keys: 'date','milestone','confidence','sources','notes'.\n"
    )
    # LLM call (ChatCompletion)
    try:
        resp = openai.ChatCompletion.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You output strict factual summaries based only on input text. Do not hallucinate."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.0
        )
        text = resp.choices[0].message["content"]
        # try to parse JSON out of the answer
        # LLM is asked to respond in JSON; we try to find the JSON substring
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end != -1:
            j = json.loads(text[start:end])
            return j
        else:
            # fallback: wrap minimal output
            return {"date": candidate_date, "milestone": text.strip(), "confidence": 0.5, "sources": [], "notes": ""}
    except Exception as e:
        # LLM failed — build a simple fallback summary
        sentence = cluster[0]["sentence"][:240]
        return {"date": candidate_date, "milestone": sentence, "confidence": 0.4, "sources": list({c["article_source"] for c in cluster})[:3], "notes": f"LLM error: {e}"}

def build_timeline(candidates):
    """
    Full pipeline: cluster -> canonical date -> LLM summarize -> produce timeline entries
    """
    clusters = cluster_candidates(candidates)
    timeline = []
    for cl in clusters:
        c_date = canonical_date_for_cluster(cl)
        summary = summarize_cluster_with_llm(cl, c_date)
        timeline.append({
            "date": summary.get("date") or c_date,
            "milestone": summary.get("milestone"),
            "confidence": summary.get("confidence"),
            "sources": summary.get("sources"),
            "notes": summary.get("notes"),
            "supporting_sentences": [ {"sentence": s["sentence"], "source": s["article_source"], "url": s["article_url"]} for s in cl]
        })
    # sort timeline by date (None goes last)
    def parse_none(d):
        try:
            return parse_dt(d)
        except Exception:
            return None
    timeline_sorted = sorted(timeline, key=lambda x: parse_dt(x["date"]) if x["date"] else datetime.max)
    return timeline_sorted
