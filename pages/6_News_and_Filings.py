"""
News & Filings
──────────────
NSE corporate announcements, order wins, results, concall summaries.
AI-classified by impact, materiality, and sentiment.
"""

import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="News & Filings — India Terminal",
    layout="wide", initial_sidebar_state="expanded",
)

from utils.formatting import (
    inject_css, page_header, section_label, kpi_card, fmt_pct,
    info_block, warn_block, ai_box, sentiment_badge, ACCENT, POS, NEG, TEXT3,
)
from utils.data_loader import load_filings, load_news, load_universe
from utils.nse_fetcher import fetch_corporate_announcements
import utils.ai_summarizer as ai

inject_css()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sec-label">Filters</div>', unsafe_allow_html=True)

    FILING_TYPES = ["All Types","Order Win","Results","Board Meeting","AGM",
                    "Dividend","Credit Rating","Investor Presentation",
                    "Promoter Pledge","Management Change","Fundraise","General"]
    type_f = st.selectbox("Filing Type", FILING_TYPES)

    SENTIMENTS = ["All", "Positive", "Negative", "Neutral"]
    sent_f = st.selectbox("Sentiment", SENTIMENTS)

    material_only = st.checkbox("Material Only", value=False)

    uni = load_universe()
    tickers = ["All Tickers"] + (sorted(uni["ticker"].tolist()) if not uni.empty else [])
    ticker_f = st.selectbox("Company / Ticker", tickers)

    n_days = st.slider("Days Back", 1, 30, 7)

    st.markdown("---")
    live_fetch = st.button("Fetch Live NSE Announcements")

page_header("News & Filings", f"Corporate announcements and market intelligence")

# ── Fetch live if requested ───────────────────────────────────────────────────
if live_fetch:
    with st.spinner("Fetching NSE corporate announcements…"):
        live_df = fetch_corporate_announcements(n_days=n_days)
    if live_df.empty:
        warn_block("Could not fetch live NSE data. Check internet connection or session cookies.")
    else:
        from utils.data_loader import DATA, FILINGS_CSV
        import os
        existing = load_filings()
        combined = pd.concat([live_df, existing], ignore_index=True)
        combined = combined.drop_duplicates(subset=["ticker","date","subject"] if all(c in combined.columns for c in ["ticker","date","subject"]) else combined.columns[:3])
        combined.to_csv(FILINGS_CSV, index=False)
        st.success(f"Fetched {len(live_df)} announcements from NSE. Data saved.")
        st.rerun()

# ── Load data ─────────────────────────────────────────────────────────────────
filings = load_filings()
news    = load_news()

# ── Summary KPIs ──────────────────────────────────────────────────────────────
section_label("Today's Summary")

n_fil     = len(filings) if not filings.empty else 0
n_mat     = filings["is_material"].sum() if not filings.empty and "is_material" in filings.columns else 0
n_order_w = (filings["type"] == "Order Win").sum() if not filings.empty and "type" in filings.columns else 0
n_pos     = (filings.get("sentiment","") == "positive").sum() if not filings.empty else 0

kcols = st.columns(5)
kpi_data = [
    ("Total Filings",   str(n_fil),  ""),
    ("Material",        str(n_mat),  "High impact"),
    ("Order Wins",      str(n_order_w), ""),
    ("Positive",        str(n_pos),  ""),
    ("News Items",      str(len(news)) if not news.empty else "0", ""),
]
for col, (l, v, s) in zip(kcols, kpi_data):
    with col:
        kpi_card(l, v, s)

st.markdown("<br>", unsafe_allow_html=True)

# ── Apply filters to filings ──────────────────────────────────────────────────
def _filter_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if type_f != "All Types" and "type" in df.columns:
        df = df[df["type"] == type_f]
    if sent_f != "All" and "sentiment" in df.columns:
        df = df[df["sentiment"].str.lower() == sent_f.lower()]
    if material_only and "is_material" in df.columns:
        df = df[df["is_material"] == True]
    if ticker_f != "All Tickers" and "ticker" in df.columns:
        df = df[df["ticker"] == ticker_f]
    return df

fil_f = _filter_df(filings.copy()) if not filings.empty else pd.DataFrame()
news_f = _filter_df(news.copy()) if not news.empty else pd.DataFrame()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "Corporate Filings", "News Feed", "Order Wins", "Material Events",
])

def _render_filing_row(row):
    s = str(row.get("sentiment", "neutral")).lower()
    col_map = {"positive": "#22c55e", "negative": "#ef4444", "neutral": "#64748b"}
    c = col_map.get(s, "#64748b")
    ftype = row.get("type", "Filing")
    ai_s  = row.get("ai_summary", "")
    ai_html = f'<div class="fil-ai">{ai_s}</div>' if ai_s else ""
    mat_badge = (
        ' &nbsp;<span class="badge" style="background:#1c1100;color:#f59e0b;'
        'border:1px solid #92400e;">MATERIAL</span>'
        if row.get("is_material") else ""
    )
    url = row.get("url", "")
    url_html = (
        f' &nbsp;<a href="{url}" target="_blank" style="font-size:0.68rem;color:#3b82f6;">[Source]</a>'
        if url and url.startswith("http") else ""
    )
    st.markdown(
        f"""<div class="fil-row">
              <div style="display:flex;flex-direction:column;gap:0.1rem;min-width:5rem;">
                <div class="fil-time">{str(row.get('date',''))[:10]}</div>
                <div class="fil-time">{str(row.get('time',''))}</div>
              </div>
              <div class="fil-body">
                <div class="fil-title">
                  <span style="color:#3b82f6;font-weight:600;">{row.get('ticker','')}</span>
                  &nbsp;&mdash;&nbsp;{row.get('subject','')}
                  {url_html}
                </div>
                <div class="fil-meta">
                  <span class="badge" style="background:#0f1929;border:1px solid {c};color:{c};">
                    {s.upper()}</span>
                  &nbsp;|&nbsp; {ftype}
                  {mat_badge}
                </div>
                {ai_html}
              </div>
            </div>""",
        unsafe_allow_html=True,
    )


def _render_news_row(row):
    s = str(row.get("sentiment", "neutral")).lower()
    col_map = {"positive": "#22c55e", "negative": "#ef4444", "neutral": "#64748b"}
    c = col_map.get(s, "#64748b")
    tickers = row.get("tickers_mentioned", "")
    tick_html = ""
    if tickers:
        tick_html = "".join(
            f'<span class="idea-tag" style="color:#3b82f6;">{t.strip()}</span>'
            for t in str(tickers).split("|") if t.strip()
        )
    st.markdown(
        f"""<div class="fil-row">
              <div class="fil-time">{str(row.get('date',''))[:10]}</div>
              <div class="fil-body">
                <div class="fil-title">{row.get('headline','')}</div>
                <div class="fil-meta">
                  {row.get('source','')} &nbsp;|&nbsp;
                  <span class="badge" style="background:#0f1929;border:1px solid {c};color:{c};">
                    {s.upper()}</span>
                  &nbsp;|&nbsp; {row.get('sector','')}
                </div>
                <div class="idea-grid">{tick_html}</div>
                <div class="fil-ai">{row.get('ai_summary','')}</div>
              </div>
            </div>""",
        unsafe_allow_html=True,
    )


with tab1:
    section_label(f"Corporate Filings — {len(fil_f)} items")
    if fil_f.empty:
        info_block(
            "No filings found. "
            "Click 'Fetch Live NSE Announcements' in the sidebar, "
            "or populate data/filings.csv."
        )
    else:
        for _, row in fil_f.iterrows():
            _render_filing_row(row)

with tab2:
    section_label(f"News Feed — {len(news_f)} items")
    if news_f.empty:
        info_block("No news items found. Populate data/news.csv.")
    else:
        for _, row in news_f.iterrows():
            _render_news_row(row)

with tab3:
    section_label("Order Win Announcements")
    if not filings.empty and "type" in filings.columns:
        orders = filings[filings["type"] == "Order Win"]
        if orders.empty:
            info_block("No order win filings in database.")
        else:
            for _, row in orders.iterrows():
                _render_filing_row(row)
    else:
        info_block("No filings data available.")

with tab4:
    section_label("Material Events")
    if not filings.empty and "is_material" in filings.columns:
        mat = filings[filings["is_material"] == True]
        if mat.empty:
            info_block("No material events flagged.")
        else:
            for _, row in mat.iterrows():
                _render_filing_row(row)
    else:
        info_block("No filings data available.")

# ── AI batch summarise ────────────────────────────────────────────────────────
st.markdown("---")
section_label("AI-Assisted Filing Summarisation")
if st.button("Summarise All Unsummarised Filings (requires Claude API key)"):
    if filings.empty:
        st.warning("No filings to summarise.")
    else:
        count = 0
        progress = st.progress(0)
        for i, (idx, row) in enumerate(filings.iterrows()):
            if not row.get("ai_summary"):
                result = ai.summarize_filing(
                    ticker   = row.get("ticker", ""),
                    company  = row.get("company_name", ""),
                    subject  = row.get("subject", ""),
                    filing_type = row.get("type", ""),
                )
                filings.at[idx, "ai_summary"]   = result.get("summary", "")
                filings.at[idx, "sentiment"]    = result.get("sentiment", "neutral")
                filings.at[idx, "is_material"]  = result.get("is_material", False)
                count += 1
            progress.progress((i + 1) / len(filings))
        from utils.data_loader import FILINGS_CSV
        filings.to_csv(FILINGS_CSV, index=False)
        st.success(f"Summarised {count} filings.")
