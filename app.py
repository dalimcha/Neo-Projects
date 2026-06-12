from __future__ import annotations

from html import escape
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="India Public Markets Intelligence Terminal",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.auth import require_password
from utils.formatting import inject_css, page_header, section_label, index_card, table_wrap, info_block, html_block
from utils.data_loader import (
    build_morning_brief,
    load_universe,
    load_returns_snapshot,
    load_sector_performance,
    load_filings,
    load_news,
    load_full_universe,
)
from utils.validation import build_universe_report
from utils.nse_fetcher import fetch_index_snapshot


inject_css()
require_password()


def _stamp(report, ts: str | None) -> str:
    updated = ts or "N/A"
    return f"{report.universe} · {report.valid_price_rows}/{report.expected_count} · Updated {updated} IST"


def _latest_price_ts(snapshot: pd.DataFrame) -> str | None:
    if snapshot.empty or "price_timestamp" not in snapshot.columns:
        return None
    ts = pd.to_datetime(snapshot["price_timestamp"], errors="coerce").max()
    if pd.isna(ts):
        return None
    return ts.strftime("%d %b %H:%M")


def _top_story_rows(snapshot: pd.DataFrame, filings_df: pd.DataFrame, news_df: pd.DataFrame) -> str:
    if snapshot.empty:
        return ""
    events = {}
    if not filings_df.empty and {"ticker", "subject"}.issubset(filings_df.columns):
        tmp = filings_df.sort_values("date", ascending=False) if "date" in filings_df.columns else filings_df
        for _, r in tmp.iterrows():
            t = str(r.get("ticker", "")).upper().strip()
            if t and t not in events:
                events[t] = str(r.get("subject", "")).strip()
    if not news_df.empty and {"tickers_mentioned", "headline"}.issubset(news_df.columns):
        tmp = news_df.sort_values("date", ascending=False) if "date" in news_df.columns else news_df
        for _, r in tmp.iterrows():
            for t in [x.strip().upper() for x in str(r.get("tickers_mentioned", "")).split("|") if x.strip()]:
                if t and t not in events:
                    events[t] = str(r.get("headline", "")).strip()
    movers = snapshot.copy()
    movers["ret_abs"] = pd.to_numeric(movers["return_1d"], errors="coerce").abs()
    movers = movers[movers["ticker"].astype(str).str.upper().isin(events)]
    movers = movers.sort_values("ret_abs", ascending=False).head(5)
    rows = ""
    for _, r in movers.iterrows():
        rows += (
            "<tr>"
            f"<td class='ticker'>{r['ticker']}</td>"
            f"<td class='name'>{r.get('company_name','')}</td>"
            f"<td>{float(r['return_1d'])*100:+.1f}%</td>"
            f"<td style='text-align:left;max-width:320px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{events.get(str(r['ticker']).upper(), '')}</td>"
            "</tr>"
        )
    return rows


def _sector_pulse_rows(sector_df: pd.DataFrame) -> str:
    if sector_df.empty:
        return ""
    sub = sector_df.sort_values("avg_return_1d", ascending=False).head(8)
    rows = ""
    for _, r in sub.iterrows():
        rows += (
            "<tr>"
            f"<td class='left'>{r.get('sector','')}</td>"
            f"<td>{float(r.get('avg_return_1d',0))*100:+.1f}%</td>"
            f"<td>{float(r.get('avg_return_1m',0))*100:+.1f}%</td>"
            f"<td>{int(r.get('advancers',0))}/{int(r.get('decliners',0))}</td>"
            "</tr>"
        )
    return rows


def _watch_rows(full_df: pd.DataFrame) -> str:
    if full_df.empty:
        return ""
    sub = full_df.dropna(subset=["return_1d"]).sort_values("return_1d", ascending=False).head(8)
    rows = ""
    for _, r in sub.iterrows():
        rows += (
            "<tr>"
            f"<td class='ticker'>{r.get('ticker','')}</td>"
            f"<td class='name'>{r.get('company_name','')}</td>"
            f"<td>{float(r.get('return_1d',0))*100:+.1f}%</td>"
            f"<td>{r.get('sector','')}</td>"
            "</tr>"
        )
    return rows


returns_df = load_returns_snapshot()
sector_df = load_sector_performance()
filings_df = load_filings()
news_df = load_news()
universe_df = load_universe()
full_df = load_full_universe()
indices = fetch_index_snapshot() or {}

report = build_universe_report(
    universe_label="Nifty 500",
    universe_df=universe_df,
    prices_df=returns_df.rename(columns={"price": "close"}),
    fundamentals_df=full_df,
    news_df=news_df,
    source_prices="returns_snapshot.csv",
    source_fundamentals="fundamentals.csv",
    source_news="filings.csv / news.csv",
)

price_ts = _latest_price_ts(returns_df)
page_header(
    "India Public Markets Intelligence Terminal",
    "Daily operating board for market pulse, company research, and catalyst monitoring.",
    ts=False,
    data_status="Fresh" if report.passes else "Delayed",
    stamp_text=_stamp(report, price_ts),
    paused_message=None if report.passes else f"Universe incomplete ({report.valid_price_rows}/{report.expected_count}) — analytics paused",
)

index_config = [
    ("nifty50", "Nifty 50", "NSE"),
    ("niftyNext50", "Nifty Next 50", "NSE"),
    ("nifty500", "Nifty 500", "NSE"),
    ("bankNifty", "Bank Nifty", "NSE"),
    ("sensex", "Sensex", "BSE"),
    ("vix", "India VIX", "NSE"),
]
visible = [(k, l, s) for (k, l, s) in index_config if k in indices and indices[k].get("value") is not None]
if visible:
    cols = st.columns(len(visible))
    for col, (key, label, source) in zip(cols, visible):
        with col:
            d = indices[key]
            prev = float(d.get("value", 0)) - float(d.get("change", 0) or 0)
            pts = f"{float(d.get('change', 0)):+,.0f}" if prev else ""
            index_card(
                name=label,
                value=f"{d.get('value', 0):,.2f}",
                change=f"{d.get('change_pct', 0):+.2f}%",
                pts=pts if prev else "",
                is_up=None if key == "vix" else (float(d.get("change_pct", 0) or 0) >= 0),
                source=source,
                data_ts=price_ts or "",
            )

brief_lines = build_morning_brief(returns_df, sector_df, indices, filings_df, news_df)
html_block(
    f"""
    <div class="hero-panel">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap;">
        <div>
          <div class="hero-kicker">Operating Brief</div>
          <div class="hero-title">Today&apos;s Market Operating Board</div>
          <div class="hero-sub">Use this surface to open the day fast: market tone, linked catalysts, sector pulse, and the live research grid.</div>
        </div>
        <div style="display:flex;gap:0.55rem;flex-wrap:wrap;justify-content:flex-end;">
          <span class="pill-chip"><strong>Universe</strong>{report.valid_price_rows}/{report.expected_count}</span>
          <span class="pill-chip"><strong>Filings</strong>{len(filings_df)}</span>
          <span class="pill-chip"><strong>News</strong>{len(news_df)}</span>
        </div>
      </div>
    </div>
    """
)
html_block(
    "<div class='surface-box'>"
    "<div class='surface-title'>Morning Brief</div>"
    "<div class='surface-note'>" + "<br>".join(escape(line) for line in brief_lines) + "</div>"
    "</div>"
)
st.download_button("Copy Morning Brief", data="\n".join(brief_lines), file_name="morning_brief.txt", mime="text/plain")

section_label("Today's Signal")
c1, c2, c3 = st.columns(3, gap="large")
with c1:
    rows = _top_story_rows(returns_df, filings_df, news_df)
    if rows:
        table_wrap(
            f"<table class='trm'><thead><tr><th class='left'>Ticker</th><th class='left'>Company</th><th>1D</th><th class='left'>Catalyst</th></tr></thead><tbody>{rows}</tbody></table>",
            caption="Biggest Stories",
            caption_right="Top movers with real catalysts",
        )
    else:
        info_block("No catalyst-linked movers available yet.")
with c2:
    rows = _sector_pulse_rows(sector_df)
    if rows:
        table_wrap(
            f"<table class='trm'><thead><tr><th class='left'>Sector</th><th>1D</th><th>1M</th><th>A/D</th></tr></thead><tbody>{rows}</tbody></table>",
            caption="Sector Pulse",
            caption_right="1D / 1M leadership",
        )
    else:
        info_block("Sector performance not available.")
with c3:
    rows = _watch_rows(full_df)
    if rows:
        table_wrap(
            f"<table class='trm'><thead><tr><th class='left'>Ticker</th><th class='left'>Company</th><th>1D</th><th class='left'>Sector</th></tr></thead><tbody>{rows}</tbody></table>",
            caption="Watching",
            caption_right="Move leaders today",
        )
    else:
        info_block("No watch rows available.")

section_label("Watching")
left, mid, right = st.columns(3, gap="large")
with left:
    st.page_link("pages/2_All_Companies.py", label="All Companies", icon=":material/table_view:")
    st.page_link("pages/5_New_Ideas.py", label="Ideas Lab", icon=":material/lightbulb:")
with mid:
    st.page_link("pages/6_News_and_Filings.py", label="News & Filings", icon=":material/feed:")
    st.page_link("pages/10_Earnings.py", label="Earnings", icon=":material/calendar_month:")
with right:
    st.page_link("pages/1_Market_Command_Center.py", label="Market Command Center", icon=":material/monitoring:")
    st.page_link("pages/9_Return_Quartiles.py", label="Return Quartiles", icon=":material/grid_view:")
