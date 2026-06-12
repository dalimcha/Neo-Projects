from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="News & Filings — India Terminal",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.formatting import (
    inject_css,
    page_header,
    section_label,
    kpi_card,
    info_block,
    warn_block,
    table_wrap,
    sentiment_badge,
    html_block,
)
from utils.data_loader import (
    ROOT,
    load_data_quality_log,
    load_failed_tickers,
    load_filings,
    load_news,
    load_returns_snapshot,
    load_universe,
)


inject_css()

DEBUG_MODE = str(st.query_params.get("debug", "0")) == "1"


def _last_refresh(log_df: pd.DataFrame, dataset: str) -> tuple[str, str]:
    if log_df.empty or "dataset" not in log_df.columns:
        return "N/A", "N/A"
    sub = log_df[log_df["dataset"].astype(str) == dataset].copy()
    if sub.empty:
        return "N/A", "N/A"
    if "logged_at" in sub.columns:
        sub["logged_at"] = pd.to_datetime(sub["logged_at"], errors="coerce")
        sub = sub.sort_values("logged_at")
    row = sub.iloc[-1]
    status = str(row.get("status", "N/A"))
    ts = row.get("last_refresh_at")
    if pd.notna(ts):
        ts = pd.to_datetime(ts, errors="coerce")
        ts_str = ts.strftime("%d %b %Y %H:%M")
    else:
        ts_str = "N/A"
    return status, ts_str


def _fallback_dataset_status(df: pd.DataFrame) -> tuple[str, str]:
    if df.empty or "date" not in df.columns:
        return "N/A", "N/A"
    ts = pd.to_datetime(df["date"], errors="coerce").max()
    if pd.isna(ts):
        return "N/A", "N/A"
    age_days = (pd.Timestamp.now() - ts).days
    if age_days <= 2:
        status = "Fresh"
    elif age_days <= 7:
        status = "Delayed"
    elif age_days <= 30:
        status = "Stale"
    else:
        status = "Cached"
    return status, ts.strftime("%d %b %Y %H:%M")


def _safe_text(value: object, fallback: str = "N/A") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _suggested_action(row: pd.Series, mode: str) -> str:
    score = int(pd.to_numeric(row.get("materiality_score"), errors="coerce") or 0)
    sentiment = str(row.get("sentiment", "neutral")).strip().lower()
    event_type = str(row.get("type" if mode == "filings" else "categories", "")).strip().lower()
    if score >= 85 or ("result" in event_type and sentiment == "positive"):
        return "Review Now"
    if score >= 70 or ("order" in event_type and sentiment != "negative"):
        return "Add to Queue"
    if sentiment == "negative" and score >= 55:
        return "Risk Check"
    if score >= 40 or sentiment == "positive":
        return "Watch"
    return "Ignore"


def _run_script(script_name: str, args: list[str] | None = None) -> tuple[bool, str]:
    script = ROOT / "scripts" / script_name
    cmd = [sys.executable, str(script)] + (args or [])
    try:
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        return False, str(exc)

    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode == 0, out.strip()


def _filter_news_by_ticker(news_df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if news_df.empty or ticker == "All":
        return news_df
    if "tickers_mentioned" not in news_df.columns:
        return news_df.iloc[0:0]
    return news_df[news_df["tickers_mentioned"].astype(str).str.contains(ticker, na=False)]


def _latest_event_map(df: pd.DataFrame, key_col: str, text_col: str) -> dict[str, str]:
    if df.empty or key_col not in df.columns or text_col not in df.columns:
        return {}
    tmp = df.copy()
    if "date" in tmp.columns:
        tmp["date"] = pd.to_datetime(tmp["date"], errors="coerce")
        tmp = tmp.sort_values("date", ascending=False)
    result: dict[str, str] = {}
    for _, row in tmp.iterrows():
        key = str(row.get(key_col, "")).strip().upper()
        text = str(row.get(text_col, "")).strip()
        if key and text and key not in result:
            result[key] = text
    return result


def _render_event_rows(df: pd.DataFrame, mode: str) -> None:
    if df.empty:
        info_block("No items matched the current filters.")
        return

    rows = ""
    for _, row in df.iterrows():
        ticker = _safe_text(row.get("ticker")) if mode == "filings" else _safe_text(row.get("tickers_mentioned"))
        company = _safe_text(row.get("company_name")) if mode == "filings" else _safe_text(row.get("sector"))
        headline = _safe_text(row.get("subject")) if mode == "filings" else _safe_text(row.get("headline"))
        source = _safe_text(row.get("source"))
        event_type = _safe_text(row.get("type")) if mode == "filings" else _safe_text(row.get("categories"))
        sentiment = str(row.get("sentiment", "")).strip().lower() or "neutral"
        summary = _safe_text(row.get("ai_summary"), "")
        url = _safe_text(row.get("source_url")) if mode == "filings" else _safe_text(row.get("url"))
        is_material = bool(row.get("is_material", False))
        date_val = row.get("date")
        date_str = pd.to_datetime(date_val, errors="coerce").strftime("%d %b %Y") if pd.notna(pd.to_datetime(date_val, errors="coerce")) else "N/A"
        link_html = f"<a href='{url}' target='_blank' style='color:#60a5fa;'>Open</a>" if url != "N/A" else "N/A"
        material = f"{int(pd.to_numeric(row.get('materiality_score'), errors='coerce') or 0)}" if is_material else "0"
        sentiment_html = sentiment_badge(sentiment)
        summary_cell = summary if summary else "No AI summary yet."
        action = _suggested_action(row, mode)
        rows += (
            "<tr>"
            f"<td class='ticker'>{ticker}</td>"
            f"<td class='name'>{company}</td>"
            f"<td style='text-align:left;max-width:360px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{headline}</td>"
            f"<td class='left'>{event_type}</td>"
            f"<td>{sentiment_html}</td>"
            f"<td>{material}</td>"
            f"<td>{action}</td>"
            f"<td class='left'>{source}</td>"
            f"<td class='left' style='max-width:300px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{summary_cell}</td>"
            f"<td>{date_str}</td>"
            f"<td>{link_html}</td>"
            "</tr>"
        )

    table_wrap(
        f"""<table class='trm'>
            <thead><tr>
              <th class='left'>Ticker</th>
              <th class='left'>Company/Sector</th>
              <th class='left'>Headline</th>
              <th class='left'>Type</th>
              <th>Sentiment</th>
              <th>Score</th>
              <th>Action</th>
              <th class='left'>Source</th>
              <th class='left'>Summary</th>
              <th>Date</th>
              <th>Link</th>
            </tr></thead>
            <tbody>{rows}</tbody>
           </table>""",
        caption=f"{len(df)} rows",
        caption_right="Canonical source: data/news.csv + data/filings.csv",
    )


universe_df = load_universe()
returns_df = load_returns_snapshot()
filings_df = load_filings()
news_df = load_news()
quality_log_df = load_data_quality_log()
failed_df = load_failed_tickers()

filings_status, filings_ts = _last_refresh(quality_log_df, "filings")
news_status, news_ts = _last_refresh(quality_log_df, "news")
if filings_status == "N/A":
    filings_status, filings_ts = _fallback_dataset_status(filings_df)
if news_status == "N/A":
    news_status, news_ts = _fallback_dataset_status(news_df)

with st.sidebar:
    html_block('<div class="sec-label">Refresh</div>')
    if st.button("Update Filings"):
        ok, output = _run_script("update_filings.py")
        if ok:
            st.success("Filings refresh completed.")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Filings refresh failed.")
            st.code(output or "No output captured.")

    if st.button("Update News"):
        ok, output = _run_script("update_news.py")
        if ok:
            st.success("News refresh completed.")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("News refresh failed.")
            st.code(output or "No output captured.")

    st.markdown("---")
    html_block('<div class="sec-label">Filters</div>')
    ticker_opts = ["All"] + sorted(universe_df["ticker"].dropna().astype(str).str.upper().unique().tolist()) if not universe_df.empty else ["All"]
    sector_opts = ["All"] + sorted(universe_df["sector"].dropna().astype(str).unique().tolist()) if not universe_df.empty else ["All"]
    type_opts = ["All"]
    if not filings_df.empty and "type" in filings_df.columns:
        type_opts += sorted([x for x in filings_df["type"].dropna().astype(str).unique().tolist() if x])
    sentiment_opts = ["All", "positive", "negative", "neutral"]

    ticker_filter = st.selectbox("Ticker", ticker_opts)
    sector_filter = st.selectbox("Sector", sector_opts)
    type_filter = st.selectbox("Filing Type", type_opts)
    sentiment_filter = st.selectbox("Sentiment", sentiment_opts)
    material_only = st.checkbox("Material Only", value=False)
    latest_event_dt = pd.NaT
    if not filings_df.empty and "date" in filings_df.columns:
        latest_event_dt = pd.to_datetime(filings_df["date"], errors="coerce").max()
    if not news_df.empty and "date" in news_df.columns:
        latest_news_dt = pd.to_datetime(news_df["date"], errors="coerce").max()
        if pd.notna(latest_news_dt) and (pd.isna(latest_event_dt) or latest_news_dt > latest_event_dt):
            latest_event_dt = latest_news_dt
    default_days = 30
    if pd.notna(latest_event_dt) and (pd.Timestamp.now() - latest_event_dt).days > 30:
        default_days = 730
    days_back = st.slider("Days Back", min_value=1, max_value=730, value=default_days)

page_header("", "")

material_items = 0
if not filings_df.empty and "is_material" in filings_df.columns:
    material_items += int(filings_df["is_material"].fillna(False).sum())
if not news_df.empty and "is_material" in news_df.columns:
    material_items += int(news_df["is_material"].fillna(False).sum())

html_block(
    f"""<div class="hero-panel">
          <div class="hero-kicker">Event Tape</div>
          <div class="hero-title">News and Filings</div>
          <div class="hero-sub">Actionability-first event layer for daily catalyst detection, mover attribution, and meeting prep.</div>
          <div style="margin-top:0.55rem;display:flex;gap:0.45rem;flex-wrap:wrap;">
            <span class="chip">Material {material_items}</span>
            <span class="chip">Filings {len(filings_df)}</span>
            <span class="chip">News {len(news_df)}</span>
            <span class="chip">Universe {len(universe_df)}</span>
          </div>
        </div>"""
)

if filings_status in {"Failed", "Stale"} and news_status in {"Failed", "Stale"}:
    warn_block("Both event feeds are stale or failed. Refresh filings and news before relying on move explanations.")
elif filings_status == "Cached" or news_status == "Cached":
    info_block("Using cached event data. Refresh filings and news to restore daily catalyst coverage.")

section_label("Signal")
latest_filing_map = _latest_event_map(filings_df, "ticker", "subject")
latest_news_map: dict[str, str] = {}
if not news_df.empty and "tickers_mentioned" in news_df.columns:
    tmp_news = news_df.copy()
    if "date" in tmp_news.columns:
        tmp_news["date"] = pd.to_datetime(tmp_news["date"], errors="coerce")
        tmp_news = tmp_news.sort_values("date", ascending=False)
    for _, row in tmp_news.iterrows():
        headline = str(row.get("headline", "")).strip()
        for ticker in [x.strip().upper() for x in str(row.get("tickers_mentioned", "")).split("|") if x.strip()]:
            if ticker and headline and ticker not in latest_news_map:
                latest_news_map[ticker] = headline

coverage_cols = st.columns(4)
with coverage_cols[0]:
    kpi_card("Universe", str(len(universe_df)), "Tracked stocks")
with coverage_cols[1]:
    kpi_card("Linked Filings", str(len(latest_filing_map)), "Stocks with filing context")
with coverage_cols[2]:
    kpi_card("Linked News", str(len(latest_news_map)), "Stocks with news context")
with coverage_cols[3]:
    movers_covered = 0
    if not returns_df.empty and "ticker" in returns_df.columns:
        movers = returns_df.dropna(subset=["return_1d"]).nlargest(20, "return_1d")
        movers_covered = sum(
            1 for t in movers["ticker"].astype(str).str.upper()
            if t in latest_filing_map or t in latest_news_map
        )
    kpi_card("Movers Explained", str(movers_covered), "Top-20 gainers with linked events")

if not filings_df.empty and "date" in filings_df.columns:
    filings_filtered = filings_df.copy()
    filings_filtered["date"] = pd.to_datetime(filings_filtered["date"], errors="coerce")
    filings_filtered = filings_filtered[filings_filtered["date"] >= (pd.Timestamp.now() - pd.Timedelta(days=days_back))]
else:
    filings_filtered = filings_df.copy()

if not news_df.empty and "date" in news_df.columns:
    news_filtered = news_df.copy()
    news_filtered["date"] = pd.to_datetime(news_filtered["date"], errors="coerce")
    news_filtered = news_filtered[news_filtered["date"] >= (pd.Timestamp.now() - pd.Timedelta(days=days_back))]
else:
    news_filtered = news_df.copy()

if ticker_filter != "All":
    if not filings_filtered.empty and "ticker" in filings_filtered.columns:
        filings_filtered = filings_filtered[filings_filtered["ticker"] == ticker_filter]
    news_filtered = _filter_news_by_ticker(news_filtered, ticker_filter)

if sector_filter != "All":
    if not news_filtered.empty and "sector" in news_filtered.columns:
        news_filtered = news_filtered[news_filtered["sector"] == sector_filter]
    if not filings_filtered.empty and "ticker" in filings_filtered.columns and not universe_df.empty:
        sector_tickers = set(
            universe_df.loc[universe_df["sector"] == sector_filter, "ticker"]
            .dropna().astype(str).str.upper().tolist()
        )
        filings_filtered = filings_filtered[filings_filtered["ticker"].isin(sector_tickers)]

if type_filter != "All" and not filings_filtered.empty and "type" in filings_filtered.columns:
    filings_filtered = filings_filtered[filings_filtered["type"] == type_filter]

if sentiment_filter != "All":
    if not filings_filtered.empty and "sentiment" in filings_filtered.columns:
        filings_filtered = filings_filtered[filings_filtered["sentiment"].astype(str).str.lower() == sentiment_filter]
    if not news_filtered.empty and "sentiment" in news_filtered.columns:
        news_filtered = news_filtered[news_filtered["sentiment"].astype(str).str.lower() == sentiment_filter]

if material_only:
    if not filings_filtered.empty and "is_material" in filings_filtered.columns:
        filings_filtered = filings_filtered[filings_filtered["is_material"]]
    if not news_filtered.empty and "is_material" in news_filtered.columns:
        news_filtered = news_filtered[news_filtered["is_material"]]

tab1, tab2, tab3, tab4 = st.tabs([
    "Filings",
    "News",
    "Material",
    "Mover Context",
])

with tab1:
    section_label("Canonical Filings Feed")
    _render_event_rows(filings_filtered.head(200), mode="filings")

with tab2:
    section_label("Canonical News Feed")
    _render_event_rows(news_filtered.head(200), mode="news")

with tab3:
    section_label("Material Events")
    material_filings = filings_filtered[filings_filtered["is_material"]] if not filings_filtered.empty and "is_material" in filings_filtered.columns else filings_filtered.iloc[0:0]
    material_news = news_filtered[news_filtered["is_material"]] if not news_filtered.empty and "is_material" in news_filtered.columns else news_filtered.iloc[0:0]
    if material_filings.empty and material_news.empty:
        info_block("No material events matched the current filters.")
    else:
        if not material_filings.empty:
            section_label("Material Filings")
            _render_event_rows(material_filings.head(100), mode="filings")
        if not material_news.empty:
            section_label("Material News")
            _render_event_rows(material_news.head(100), mode="news")

with tab4:
    section_label("Biggest Movers With Linked Events")
    if returns_df.empty or "return_1d" not in returns_df.columns:
        info_block("No return snapshot available.")
    else:
        movers = returns_df.dropna(subset=["return_1d"]).copy()
        movers = movers.sort_values("return_1d", ascending=False).head(20)
        rows = ""
        for _, row in movers.iterrows():
            ticker = str(row.get("ticker", "")).upper()
            filing = latest_filing_map.get(ticker, "No filing linked")
            news = latest_news_map.get(ticker, "No news linked")
            rows += (
                "<tr>"
                f"<td class='ticker'>{ticker}</td>"
                f"<td class='name'>{row.get('company_name', '')}</td>"
                f"<td class='left'>{row.get('sector', 'N/A')}</td>"
                f"<td>{row.get('return_1d', float('nan')) * 100:.2f}%</td>"
                f"<td>{row.get('return_1w', float('nan')) * 100:.2f}%</td>"
                f"<td>{row.get('volume_ratio_30d', float('nan')):.2f}x</td>"
                f"<td class='left' style='max-width:300px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{filing}</td>"
                f"<td class='left' style='max-width:300px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{news}</td>"
                "</tr>"
            )
        table_wrap(
            f"""<table class='trm'>
                <thead><tr>
                  <th class='left'>Ticker</th>
                  <th class='left'>Company</th>
                  <th class='left'>Sector</th>
                  <th>1D</th>
                  <th>1W</th>
                  <th>Vol/30D</th>
                  <th class='left'>Latest Filing</th>
                  <th class='left'>Latest News</th>
                </tr></thead>
                <tbody>{rows}</tbody>
               </table>""",
            caption="Top 20 gainers",
            caption_right="Used by Biggest Movers workflow",
        )

if DEBUG_MODE and not failed_df.empty:
    recent_failures = failed_df[
        failed_df["dataset"].astype(str).isin(["news", "filings"])
    ].head(10).copy()
    if not recent_failures.empty:
        rows = ""
        for _, row in recent_failures.iterrows():
            failed_at = pd.to_datetime(row.get("failed_at"), errors="coerce")
            failed_at_str = failed_at.strftime("%d %b %H:%M") if pd.notna(failed_at) else "N/A"
            rows += (
                "<tr>"
                f"<td class='left'>{_safe_text(row.get('dataset'))}</td>"
                f"<td class='ticker'>{_safe_text(row.get('ticker'))}</td>"
                f"<td class='left'>{_safe_text(row.get('stage'))}</td>"
                f"<td class='left' style='max-width:420px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{_safe_text(row.get('error_message'))}</td>"
                f"<td>{failed_at_str}</td>"
                "</tr>"
            )
        table_wrap(
            f"""<table class='trm'>
                <thead><tr>
                  <th class='left'>Dataset</th>
                  <th class='left'>Ticker/Source</th>
                  <th class='left'>Stage</th>
                  <th class='left'>Error</th>
                  <th>Failed At</th>
                </tr></thead>
                <tbody>{rows}</tbody>
               </table>""",
            caption=f"{len(recent_failures)} recent failures",
            caption_right="Canonical source: failed_tickers.csv",
        )
    else:
        info_block("No recent news/filings failures logged.")
