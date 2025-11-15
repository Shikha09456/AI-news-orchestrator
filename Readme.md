############## data flow diagram ###########

User Query
   |
Query Builder
   |
Fetcher (NewsAPI / RSS / Scraper)
   |
Article Parser (newspaper3k)
   |
Normalizer & Clean Text
   |
NLP Extraction (spaCy / dateparser)
   |
Candidate Pool (sentences with dates / keywords)
   |
Embeddings (sentence-transformers)
   |
Clustering (Agglomerative)
   |
Cluster Aggregator -> canonical date selection
   |
LLM Prompt Builder -> LLM (GPT) -> Milestone JSON
   |
Timeline Assembler (sort & merge)
   |
Veracity & Credibility Scorer
   |
Storage (DB / Cache)
   |
UI (Streamlit) + Charts & Export



############## llm workflow #############

Goal

Produce a concise, factual milestone for each cluster, with metadata: canonical date, confidence, supporting sources, and contradiction notes — without hallucination.

Inputs to the LLM (always only include this):

Cluster ID

Candidate sentences (each with: source name, full sentence text, URL, article publish date) — only direct quotes used as evidence

Candidate canonical date (computed by aggregator) and list of differing dates if present

Short system instruction that forbids adding facts not present in inputs

High-level LLM steps

System message sets strict rules (grounding, JSON output, no external facts, format).

User message contains cluster evidence and a short task prompt.

LLM returns structured JSON with: date, milestone, confidence, sources, notes.

Post-process LLM output:

Validate JSON parse

If milestone contains unsupported claims (words not present in any quote), flag and reduce confidence

If contradictions exist, ensure notes enumerates conflicting claims and their sources

Example system prompt (first message)
You are a factual summarizer. ONLY use the exact supporting quotes provided. Do NOT add outside facts or dates. Output valid JSON only. The JSON keys must be: date, milestone, confidence, sources, notes. If quotes contradict, set note to "CONTRADICTION DETECTED" and list the differing claims and their sources. Be concise: milestone 10-25 words. Confidence is a number between 0.0 and 1.0.

Example user prompt (per-cluster)
Cluster ID: 7
Candidate canonical date: 2025-02-18
Supporting quotes:
1) (TechCrunch) "OpenAI announced GPT-5 earlier today with new multimodal capabilities." URL: ...
2) (The Verge) "Sources say OpenAI released a blog post announcing GPT-5 on Feb 18." URL: ...
3) (Unknown) "Rumors suggest a GPT-5 internal rollout happened in early March." URL: ...

Task: Produce JSON with keys: date, milestone, confidence, sources, notes. Use only the quotes above; do NOT invent sources or facts. If contradictions exist, mention them in notes.

Expected LLM behavior

Prefer exact date if at least two reputable quotes show the same explicit date.

If a quote is speculative ("rumors suggest"), include but lower confidence.

If quotes directly contradict (Feb 18 vs early March), set notes to list both claims and set a lower confidence.

Keep milestone text constrained to what quotes support.

Post-LLM verification rules (automated)

Check that milestone contains only named entities or verbs present in supporting quotes. If not, mark confidence *= 0.6.

If date returned is not present in any supporting quote or article publish dates, set date = candidate canonical date and flag in notes.

Normalize date to ISO YYYY-MM-DD if possible.

3) Example outputs — realistic JSON at each stage

Below are JSON snippets you can include in documentation or demo assets. They show: raw articles, candidate sentences, clusters, and final timeline entries.

A) Raw articles (after fetch & newspaper3k parse)
[
  {
    "id": "art-001",
    "title": "OpenAI announces GPT-5 with multimodal capabilities",
    "url": "https://techcrunch.example/openai-gpt5",
    "published_at": "2025-02-18T09:12:00Z",
    "source": "TechCrunch",
    "content": "OpenAI announced GPT-5 earlier today with new multimodal capabilities that include image and audio understanding..."
  },
  {
    "id": "art-002",
    "title": "Inside OpenAI's next model: GPT-5 timeline",
    "url": "https://theverge.example/openai-gpt5-timeline",
    "published_at": "2025-02-18T10:30:00Z",
    "source": "The Verge",
    "content": "Sources say OpenAI released a blog post announcing GPT-5 on Feb 18, 2025. The post outlines performance gains..."
  },
  {
    "id": "art-003",
    "title": "Rumors of internal GPT-5 rollout continue",
    "url": "https://randomsite.example/gpt5-rumor",
    "published_at": "2025-03-05T07:00:00Z",
    "source": "RandomSite",
    "content": "Rumors suggest a GPT-5 internal rollout happened in early March, though OpenAI has not confirmed..."
  }
]

B) Candidate sentences (after sentence-splitting + date parsing + heuristics)
[
  {
    "candidate_id": "c-001",
    "article_id": "art-001",
    "source": "TechCrunch",
    "sentence": "OpenAI announced GPT-5 earlier today with new multimodal capabilities that include image and audio understanding.",
    "date_mentioned": "2025-02-18"
  },
  {
    "candidate_id": "c-002",
    "article_id": "art-002",
    "source": "The Verge",
    "sentence": "Sources say OpenAI released a blog post announcing GPT-5 on Feb 18, 2025.",
    "date_mentioned": "2025-02-18"
  },
  {
    "candidate_id": "c-003",
    "article_id": "art-003",
    "source": "RandomSite",
    "sentence": "Rumors suggest a GPT-5 internal rollout happened in early March.",
    "date_mentioned": "2025-03-01"
  }
]

C) Embeddings + clustering result (simplified)
{
  "clusters": [
    {
      "cluster_id": "cl-01",
      "members": ["c-001", "c-002"],
      "member_sources": ["TechCrunch", "The Verge"],
      "supporting_sentences": [
        {
          "source": "TechCrunch",
          "sentence": "OpenAI announced GPT-5 earlier today with new multimodal capabilities that include image and audio understanding.",
          "url": "https://techcrunch.example/openai-gpt5"
        },
        {
          "source": "The Verge",
          "sentence": "Sources say OpenAI released a blog post announcing GPT-5 on Feb 18, 2025.",
          "url": "https://theverge.example/openai-gpt5-timeline"
        }
      ],
      "candidate_dates": ["2025-02-18"]
    },
    {
      "cluster_id": "cl-02",
      "members": ["c-003"],
      "member_sources": ["RandomSite"],
      "supporting_sentences": [
        {
          "source": "RandomSite",
          "sentence": "Rumors suggest a GPT-5 internal rollout happened in early March.",
          "url": "https://randomsite.example/gpt5-rumor"
        }
      ],
      "candidate_dates": ["2025-03-01"]
    }
  ]
}

D) LLM prompt (for cluster cl-01) — what you send to the LLM
SYSTEM:
You are a factual summarizer. ONLY use the quotes below. Do NOT add facts. Output JSON with keys: date, milestone, confidence, sources, notes.

USER:
Cluster ID: cl-01
Candidate canonical date: 2025-02-18

Supporting quotes:
- (TechCrunch) "OpenAI announced GPT-5 earlier today with new multimodal capabilities that include image and audio understanding." URL: https://techcrunch.example/openai-gpt5
- (The Verge) "Sources say OpenAI released a blog post announcing GPT-5 on Feb 18, 2025." URL: https://theverge.example/openai-gpt5-timeline

Task: Using ONLY the quotes above, produce JSON: date (ISO), milestone (10-25 words), confidence (0.0-1.0), sources (list), notes (empty or contradiction info).

E) Expected LLM output (cluster cl-01)
{
  "date": "2025-02-18",
  "milestone": "OpenAI announced GPT-5 with new multimodal capabilities (image & audio understanding).",
  "confidence": 0.92,
  "sources": ["TechCrunch", "The Verge"],
  "notes": ""
}


Cluster cl-02 (rumor) expected LLM output:

{
  "date": "2025-03-01",
  "milestone": "Unconfirmed reports claim an internal GPT-5 rollout occurred in early March.",
  "confidence": 0.32,
  "sources": ["RandomSite"],
  "notes": "This claim is speculative; primary sources not confirmed."
}

F) Final assembled timeline (sorted + minimal fields)
{
  "event_query": "OpenAI GPT-5 Launch",
  "generated_at": "2025-11-15T07:20:00Z",
  "timeline": [
    {
      "date": "2025-02-18",
      "milestone": "OpenAI announced GPT-5 with new multimodal capabilities (image & audio understanding).",
      "confidence": 0.92,
      "sources": ["TechCrunch", "The Verge"],
      "supporting_sentences": [
        {
          "source": "TechCrunch",
          "sentence": "OpenAI announced GPT-5 earlier today with new multimodal capabilities that include image and audio understanding.",
          "url": "https://techcrunch.example/openai-gpt5"
        },
        {
          "source": "The Verge",
          "sentence": "Sources say OpenAI released a blog post announcing GPT-5 on Feb 18, 2025.",
          "url": "https://theverge.example/openai-gpt5-timeline"
        }
      ],
      "notes": ""
    },
    {
      "date": "2025-03-01",
      "milestone": "Unconfirmed reports claim an internal GPT-5 rollout occurred in early March.",
      "confidence": 0.32,
      "sources": ["RandomSite"],
      "supporting_sentences": [
        {
          "source": "RandomSite",
          "sentence": "Rumors suggest a GPT-5 internal rollout happened in early March.",
          "url": "https://randomsite.example/gpt5-rumor"
        }
      ],
      "notes": "Speculative claim: not corroborated by major outlets."
    }
  ],
  "source_summary": {
    "TechCrunch": 1,
    "The Verge": 1,
    "RandomSite": 1
  }
}

