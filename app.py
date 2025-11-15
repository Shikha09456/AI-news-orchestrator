# app.py
import streamlit as st
from datetime import datetime
import json
from collections import Counter, defaultdict
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from fetch_articles import fetch_articles
from process_articles import build_candidates
from timeline_builder import build_timeline

st.set_page_config(page_title="AI News Orchestrator", layout="wide", initial_sidebar_state="expanded")

# --- small css for nicer cards ---
st.markdown(
    """
    <style>
    .card { background: linear-gradient(180deg,#ffffff,#fbfbfb); border:1px solid #e6e6e6; padding:14px; border-radius:12px; margin-bottom:12px; }
    .muted { color:#6b7280; font-size:13px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----- Sidebar -----
with st.sidebar:
    st.title("📰 News Orchestrator")
    query = st.text_input("Event / Query", value="OpenAI GPT-5 Launch")
    max_articles = st.slider("Max articles", min_value=3, max_value=30, value=12)
    min_conf_pct = st.slider("Min confidence %", min_value=0, max_value=100, value=25)
    run_btn = st.button("Generate Timeline", type="primary")
    st.markdown("---")
    if st.button("Export last timeline"):
        if "last_timeline" in st.session_state:
            st.download_button(
                "Download JSON",
                json.dumps(st.session_state["last_timeline"], indent=2),
                file_name=f"timeline_{datetime.utcnow().date()}.json",
                mime="application/json",
            )
        else:
            st.warning("No timeline generated yet.")

# ----- Main header -----
st.title("AI News Orchestrator — Charts & Timeline")
st.caption("Aggregates news into a sourced timeline and visualizes evidence and confidence.")

# Initialize variables
articles = []
candidates = []
timeline = []

# Run pipeline when requested
if run_btn:
    # Fetch articles
    with st.spinner("Fetching articles..."):
        try:
            articles = fetch_articles(query, limit=max_articles)
        except Exception as e:
            st.error(f"Error fetching articles: {e}")
            articles = []

    st.success(f"Fetched {len(articles)} articles")

    # Extract candidates
    with st.spinner("Extracting candidate statements..."):
        try:
            candidates = build_candidates(articles)
        except Exception as e:
            st.error(f"Error processing articles: {e}")
            candidates = []

    st.info(f"Found {len(candidates)} candidate sentences (possible milestones).")

    # Build timeline
    with st.spinner("Building timeline (clustering + LLM summarization)..."):
        try:
            timeline = build_timeline(candidates)
        except Exception as e:
            st.error(f"Error building timeline: {e}")
            timeline = []

    # Save for export / reuse
    st.session_state["last_timeline"] = timeline
    st.session_state["last_articles"] = articles

# If we have cached timeline from previous run, use it for charts
if not timeline and "last_timeline" in st.session_state:
    timeline = st.session_state["last_timeline"]
if not articles and "last_articles" in st.session_state:
    articles = st.session_state["last_articles"]

# Sidebar: show top sources
if articles:
    st.sidebar.markdown("---")
    st.sidebar.header("Top sources")
    source_counts = {}
    for a in articles:
        s = a.get("source") or "Unknown"
        source_counts[s] = source_counts.get(s, 0) + 1
    for s, cnt in sorted(source_counts.items(), key=lambda x: -x[1]):
        badge = "🟢" if cnt >= 2 else "🟡"
        st.sidebar.markdown(f"- {badge} **{s}** — {cnt} article(s)")

# --- Layout: left columns for timeline + charts, right column for details ---
left, right = st.columns([2, 1])

with left:
    st.header("Generated Timeline")
    if not timeline:
        st.info("No timeline yet. Enter a query and click **Generate Timeline**.")
    else:
        # Filter by min confidence
        filtered = [t for t in timeline if (t.get("confidence") or 0) * 100 >= min_conf_pct]
        if not filtered:
            st.warning("No milestones match the confidence filter. Lower the min confidence to see more.")
        for idx, t in enumerate(filtered):
            date = t.get("date") or "Undated"
            milestone = t.get("milestone") or "(no summary)"
            conf = float(t.get("confidence") or 0.0)
            conf_pct = int(conf * 100)
            sources = t.get("sources") or []
            support_len = len(t.get("supporting_sentences", []))

            st.markdown(f'<div class="card"><h4>{date} — {milestone}</h4>'
                        f'<div class="muted">{support_len} supporting quote(s) • Sources: {", ".join(sources) if sources else "N/A"}</div>', unsafe_allow_html=True)
            st.markdown(f'**Confidence:** {conf_pct}%')
            if t.get("notes"):
                notes = t.get("notes")
                if "CONTRADICTION" in str(notes).upper() or "contradict" in str(notes).lower():
                    st.warning(f"⚠️ Contradiction detected: {notes}")
            # supporting quotes expandable
            with st.expander("Supporting quotes", expanded=False):
                for s in t.get("supporting_sentences", []):
                    src = s.get("source") or "Unknown"
                    sent = s.get("sentence") or ""
                    url = s.get("url")
                    st.markdown(f"- **{src}** — {sent} {'[Read](' + url + ')' if url else ''}")
            st.markdown("</div>", unsafe_allow_html=True)

    # --- Charts section ---
    st.markdown("---")
    st.header("Charts")

    if timeline:
        # Prepare data for charts
        # 1) Count supporting sentences per date
        date_counter = Counter()
        date_confidences = defaultdict(list)
        for t in timeline:
            d = t.get("date")
            # normalize undated to None
            if d is None or d == "None":
                continue
            try:
                dt = datetime.fromisoformat(d)
            except Exception:
                # try parsing common formats
                try:
                    dt = datetime.strptime(d, "%Y-%m-%d")
                except Exception:
                    continue
            # count supporting sentences (evidence)
            ev_count = len(t.get("supporting_sentences", []))
            date_counter[dt.date()] += ev_count
            # for confidence timeline (store confidence per milestone date)
            try:
                conf = float(t.get("confidence") or 0.0)
            except Exception:
                conf = 0.0
            date_confidences[dt.date()].append(conf)

        # Chart 1: Milestone evidence counts by date (bar chart)
        if date_counter:
            dates_sorted = sorted(date_counter.items(), key=lambda x: x[0])
            x_dates = [d for d, _ in dates_sorted]
            y_counts = [c for _, c in dates_sorted]

            fig1, ax1 = plt.subplots(figsize=(8, 3.2))
            ax1.bar(x_dates, y_counts)
            ax1.set_title("Supporting evidence (quotes) per date")
            ax1.set_ylabel("Number of supporting quotes")
            ax1.set_xlabel("Date")
            # format x-axis dates
            ax1.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax1.xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))
            fig1.tight_layout()
            st.pyplot(fig1)

        # Chart 2: Confidence scatter over time (median confidence per date)
        if date_confidences:
            dates2 = sorted(date_confidences.items(), key=lambda x: x[0])
            x2 = [d for d, _ in dates2]
            median_conf = [float(sorted(vals)[len(vals)//2]) if vals else 0.0 for _, vals in dates2]

            fig2, ax2 = plt.subplots(figsize=(8, 3.2))
            ax2.scatter(x2, median_conf)
            ax2.set_ylim(-0.05, 1.05)
            ax2.set_ylabel("Median confidence (0-1)")
            ax2.set_xlabel("Date")
            ax2.set_title("Median milestone confidence by date")
            ax2.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax2.xaxis.set_major_formatter(mdates.ConciseDateFormatter(mdates.AutoDateLocator()))
            fig2.tight_layout()
            st.pyplot(fig2)

        # Chart 3: Source distribution (bar chart)
        src_counts = Counter([a.get("source") or "Unknown" for a in articles])
        if src_counts:
            items = sorted(src_counts.items(), key=lambda x: x[1], reverse=True)
            labels = [it[0] for it in items]
            counts = [it[1] for it in items]

            fig3, ax3 = plt.subplots(figsize=(6, 3.2))
            ax3.bar(labels, counts)
            ax3.set_title("Article counts by source")
            ax3.set_ylabel("Number of articles")
            ax3.set_xticklabels(labels, rotation=40, ha='right')
            fig3.tight_layout()
            st.pyplot(fig3)
    else:
        st.info("Generate a timeline to see charts here.")

with right:
    st.header("Event Summary & Exploration")
    if timeline:
        # Top highlights
        st.subheader("Top highlights")
        topk = sorted(timeline, key=lambda x: (x.get("confidence") or 0), reverse=True)[:5]
        for t in topk:
            st.markdown(f"- **{t.get('date') or 'Undated'}** — {t.get('milestone')} ({int((t.get('confidence') or 0)*100)}%)")
        st.markdown("---")
        st.subheader("Selected milestone details")
        sel_idx = st.number_input("Select index (0..N-1)", min_value=0, max_value=max(0, len(timeline)-1), value=0, step=1)
        if 0 <= sel_idx < len(timeline):
            sel = timeline[sel_idx]
            st.markdown(f"**Date:** {sel.get('date') or 'Undated'}")
            st.markdown(f"**Milestone:** {sel.get('milestone') or '(none)'}")
            st.markdown(f"**Confidence:** {int((sel.get('confidence') or 0)*100)}%")
            st.markdown("**Sources:**")
            for s in sel.get("sources") or []:
                st.markdown(f"- {s}")
            st.markdown("**Supporting quotes**")
            for s in sel.get("supporting_sentences") or []:
                st.write(f"- **{s.get('source')}** — {s.get('sentence')}")
                if s.get("url"):
                    st.write(f"  [Read full article]({s.get('url')})")
            if sel.get("notes"):
                st.markdown("**Notes**")
                st.write(sel.get("notes"))
    else:
        st.info("No timeline generated yet. Press 'Generate Timeline' to begin.")

st.markdown("---")
st.caption("Charts: one plot per figure | Matplotlib rendering | Use the charts to judge evidence density and confidence trends.")
