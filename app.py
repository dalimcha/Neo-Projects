"""
India Public Markets Intelligence Terminal

Deployed entrypoint for the Streamlit multipage app.
Keep this file at repo root and point Streamlit Cloud to `app.py`.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="India Markets Terminal",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.auth import require_password
from utils.formatting import inject_css, page_header, section_label, kpi_card, info_block, warn_block
from utils.data_loader import (
    load_universe,
    load_returns_snapshot,
    load_fundamentals,
    load_data_quality_log,
    load_failed_tickers,
    load_news,
    load_filings,
)
from utils.validation import build_universe_report, render_data_quality_panel


inject_css()
require_password()


def _latest_quality_status(log_df: pd.DataFrame, dataset: str = "prices") -> tuple[str | None, str | None]:
    if log_df.empty or "dataset" not in log_df.columns:
        return None, None
    sub = log_df[log_df["dataset"].astype(str) == dataset].copy()
    if sub.empty:
        return None, None
    if "last_refresh_at" in sub.columns:
        sub["last_refresh_at"] = pd.to_datetime(sub["last_refresh_at"], errors="coerce")
        sub = sub.sort_values("last_refresh_at")
    row = sub.iloc[-1]
    ts = row.get("last_refresh_at")
    ts_str = ts.strftime("%d %b %Y %H:%M") if pd.notna(ts) else None
    status = row.get("status")
    return status.title() if isinstance(status, str) else None, ts_str


def _latest_business_note(returns_df: pd.DataFrame) -> str:
    if returns_df.empty or "return_1d" not in returns_df.columns:
        return "No canonical returns snapshot loaded yet."
    ret = pd.to_numeric(returns_df["return_1d"], errors="coerce").dropna()
    if ret.empty:
        return "Returns snapshot exists, but no valid 1D return values are available."
    adv = int((ret > 0).sum())
    dec = int((ret < 0).sum())
    avg = ret.mean() * 100
    return f"Breadth currently shows {adv} advancers vs {dec} decliners, with average 1D move {avg:+.2f}%."


quality_log_df = load_data_quality_log()
universe_df = load_universe()
returns_df = load_returns_snapshot()
fund_df = load_fundamentals()
failed_df = load_failed_tickers()
news_df = load_news()
filings_df = load_filings()

event_dates = []
if not news_df.empty and "date" in news_df.columns:
    news_dates = pd.to_datetime(news_df["date"], errors="coerce").dropna()
    if not news_dates.empty:
        event_dates.append(pd.DataFrame({"date": news_dates}))
if not filings_df.empty and "date" in filings_df.columns:
    filing_dates = pd.to_datetime(filings_df["date"], errors="coerce").dropna()
    if not filing_dates.empty:
        event_dates.append(pd.DataFrame({"date": filing_dates}))
event_df = pd.concat(event_dates, ignore_index=True) if event_dates else pd.DataFrame(columns=["date"])

report = build_universe_report(
    universe_label="Nifty 500",
    universe_df=universe_df,
    prices_df=returns_df.rename(columns={"price": "close"}),
    fundamentals_df=fund_df,
    news_df=event_df,
    failed_tickers=failed_df["ticker"].tolist() if not failed_df.empty and "ticker" in failed_df.columns else [],
    source_prices="returns_snapshot.csv",
    source_fundamentals="fundamentals.csv",
    source_news="filings.csv / news.csv",
)

status, ts = _latest_quality_status(quality_log_df, "prices")
page_header(
    "India Public Markets Intelligence Terminal",
    "Production entrypoint for the institutional tracker",
    data_status=status or report.fetch_status,
    data_ts=ts,
)

with st.sidebar:
    st.markdown(
        """
        <div style="padding:1rem 0.75rem 0.9rem;border-bottom:1px solid #0f1929;margin-bottom:0.75rem;">
          <div style="font-size:0.68rem;font-weight:800;color:#5bbcff;text-transform:uppercase;letter-spacing:0.16em;">India Markets Terminal</div>
          <div style="font-size:0.72rem;color:#89a0c2;margin-top:0.2rem;">Deployment target: repo root <code>app.py</code></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

section_label("Control Center")
render_data_quality_panel(report, compact=False)

cols = st.columns(4)
kpis = [
    ("Universe", f"{len(universe_df)}", "loaded tickers"),
    ("Valid Prices", f"{report.valid_price_rows}", "latest rows"),
    ("Fundamentals", f"{len(fund_df)}", "companies covered"),
    ("Snapshot Rows", f"{len(returns_df)}", "canonical rows"),
]
for col, (label, value, delta) in zip(cols, kpis):
    with col:
        kpi_card(label, value, delta)

st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)

st.markdown(
    f"""
    <div class="hero-panel">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap;">
        <div>
          <div class="hero-sub">Terminal Focus</div>
          <div style="
            font-family:'Syne',sans-serif;
            font-size:clamp(1.8rem,3vw,2.6rem);
            font-weight:800;
            line-height:1.02;
            letter-spacing:-0.05em;
            background:linear-gradient(135deg,#00d4ff 0%,#00ff88 100%);
            -webkit-background-clip:text;
            -webkit-text-fill-color:transparent;
            background-clip:text;
            color:transparent;
          ">Daily Market Intelligence Workflow</div>
        </div>
        <div style="display:flex;gap:0.55rem;flex-wrap:wrap;justify-content:flex-end;">
          <span class="pill-chip"><strong>Universe</strong>{len(universe_df)} names</span>
          <span class="pill-chip"><strong>Snapshot</strong>{len(returns_df)} rows</span>
          <span class="pill-chip"><strong>Fundamentals</strong>{len(fund_df)} covered</span>
          <span class="pill-chip"><strong>Events</strong>{len(news_df) + len(filings_df)} rows</span>
        </div>
      </div>
      <div class="surface-note" style="margin-top:0.85rem;">
        The operating loop is now straightforward: monitor breadth and biggest movers,
        inspect linked news and filings, then work the all-companies grid for meeting prep.
        Design density is being raised, but only on top of canonical datasets.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1.2, 1.0], gap="large")

with left:
    section_label("Start Here")
    st.page_link("pages/1_Market_Command_Center.py", label="Open Market Command Center", icon=":material/monitoring:")
    st.page_link("pages/9_Data_Quality.py", label="Open Data Quality", icon=":material/fact_check:")
    st.page_link("pages/2_All_Companies.py", label="Open All Companies", icon=":material/table_view:")
    st.page_link("pages/6_News_and_Filings.py", label="Open News & Filings", icon=":material/feed:")

    section_label("System Map")
    st.markdown(
        """
        <div class="surface">
          <div class="surface-note">
            Prices are driven by <code>data/returns_snapshot.csv</code>. Sector analytics use
            <code>data/sector_performance.csv</code>. Volume moves use <code>data/volume_shocks.csv</code>.
            Event context comes from <code>data/filings.csv</code> and <code>data/news.csv</code>.
            Refresh monitoring uses <code>data/data_quality_log.csv</code>.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right:
    section_label("Operational Note")
    note = _latest_business_note(returns_df)
    if len(fund_df) < 100:
        warn_block(
            f"{note} Price coverage is fine, but fundamentals coverage is only {len(fund_df)}/{len(universe_df)}. "
            "Import a Screener, Trendlyne, or Bloomberg fundamentals file before using valuation fields in meetings."
        )
    elif report.passes:
        info_block(
            f"{note} The tracker is using the Phase 1 canonical datasets. "
            "Next build priority is the All Companies screener and fundamentals ingestion."
        )
    else:
        warn_block(
            f"{note} The tracker is not yet trustworthy for downstream analytics because data quality gates are not passing."
        )

section_label("Immediate Next Build")
st.markdown(
    """
    <div class="surface">
      <div class="surface-title">Immediate Next Build</div>
      <div class="surface-note">
        1. Finish the event layer so biggest stock and sector movers always carry context.<br>
        2. Harden the all-companies research grid around merged returns, fundamentals, and filing metadata.<br>
        3. Import real fundamentals coverage from Screener, Trendlyne, or Bloomberg exports.<br>
        4. Push visual hierarchy, denser tables, and faster scanning once the data surface is richer.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
