"""
Data Quality

Operational page for verifying refreshes, completeness, and failures.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Data Quality — India Terminal",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.formatting import inject_css, page_header, section_label, kpi_card, table_wrap, info_block, warn_block
from utils.data_loader import (
    load_universe,
    load_fundamentals,
    load_returns_snapshot,
    load_data_quality_log,
    load_failed_tickers,
    load_volume_shocks,
    load_sector_performance,
)
from utils.validation import build_universe_report, render_data_quality_panel, UNIVERSE_SPECS


inject_css()


def _filter_universe(df: pd.DataFrame, universe_label: str) -> pd.DataFrame:
    if df.empty or universe_label == "All":
        return df
    if "index_membership" not in df.columns:
        return df
    token_map = {
        "Nifty 50": "Nifty50",
        "Nifty 100": "Nifty100",
        "Nifty 500": "Nifty500",
        "Top 1000": "Top1000",
    }
    token = token_map.get(universe_label, universe_label.replace(" ", ""))
    return df[df["index_membership"].astype(str).str.contains(token, na=False)].copy()


with st.sidebar:
    universe_label = st.selectbox("Universe", list(UNIVERSE_SPECS.keys()) + ["All"], index=2)

universe_df = load_universe()
returns_df = load_returns_snapshot()
fund_df = load_fundamentals()
quality_log_df = load_data_quality_log()
failed_df = load_failed_tickers()
volume_df = load_volume_shocks()
sector_df = load_sector_performance()

filtered_universe = _filter_universe(universe_df, universe_label)
filtered_returns = _filter_universe(returns_df, universe_label)

report = build_universe_report(
    universe_label=universe_label if universe_label in UNIVERSE_SPECS else "Nifty 500",
    universe_df=filtered_universe,
    prices_df=filtered_returns.rename(columns={"price": "close"}),
    fundamentals_df=fund_df,
    failed_tickers=failed_df["ticker"].tolist() if not failed_df.empty and "ticker" in failed_df.columns else [],
    source_prices="returns_snapshot.csv",
    source_fundamentals="fundamentals.csv",
    source_news="filings.csv / news.csv",
)

last_log_ts = None
if not quality_log_df.empty and "logged_at" in quality_log_df.columns:
    ts = pd.to_datetime(quality_log_df["logged_at"], errors="coerce").max()
    if pd.notna(ts):
        last_log_ts = ts.strftime("%d %b %Y %H:%M")

page_header("Data Quality", "Operational completeness and refresh monitoring", data_status=report.fetch_status, data_ts=last_log_ts)

render_data_quality_panel(report, compact=False)

section_label("Current Coverage")
cols = st.columns(6)
kpis = [
    ("Universe Rows", str(len(filtered_universe)), f"Expected {report.expected_count}"),
    ("Valid Prices", str(report.valid_price_rows), ""),
    ("Valid 1D Returns", str(report.valid_1d_return_rows), ""),
    ("Valid Sectors", str(report.valid_sector_rows), ""),
    ("Volume Shocks", str(len(volume_df)), ""),
    ("Sector Rows", str(len(sector_df)), ""),
]
for col, (label, value, delta) in zip(cols, kpis):
    with col:
        kpi_card(label, value, delta)

st.markdown("<br>", unsafe_allow_html=True)

section_label("Latest Quality Log")
if quality_log_df.empty:
    info_block("No data quality log rows available yet.")
else:
    show = quality_log_df.copy()
    for c in ["last_refresh_at", "logged_at"]:
        if c in show.columns:
            show[c] = pd.to_datetime(show[c], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
    rows = ""
    cols_show = [
        "dataset", "universe", "expected_rows", "loaded_rows", "valid_price_rows",
        "valid_1d_rows", "valid_sector_rows", "valid_market_cap_rows",
        "completeness_pct", "status", "source", "last_refresh_at",
    ]
    sub = show[cols_show].tail(12).iloc[::-1]
    for _, r in sub.iterrows():
        status = str(r.get("status", "")).lower()
        cls = "pos" if status == "fresh" else ("neg" if status in {"failed", "stale"} else "neu")
        rows += (
            "<tr>"
            f"<td>{r.get('dataset','')}</td>"
            f"<td>{r.get('universe','')}</td>"
            f"<td>{r.get('expected_rows','')}</td>"
            f"<td>{r.get('loaded_rows','')}</td>"
            f"<td>{r.get('valid_price_rows','')}</td>"
            f"<td>{r.get('valid_1d_rows','')}</td>"
            f"<td>{r.get('valid_sector_rows','')}</td>"
            f"<td>{r.get('valid_market_cap_rows','')}</td>"
            f"<td>{r.get('completeness_pct','')}</td>"
            f"<td class='{cls}'>{str(r.get('status','')).upper()}</td>"
            f"<td style='text-align:left;max-width:240px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{r.get('source','')}</td>"
            f"<td>{r.get('last_refresh_at','')}</td>"
            "</tr>"
        )
    table_wrap(
        f"""<table class='trm'>
            <thead><tr>
              <th>Dataset</th><th>Universe</th><th>Expected</th><th>Loaded</th>
              <th>Valid Px</th><th>Valid 1D</th><th>Valid Sector</th><th>Valid MCap</th>
              <th>Complete %</th><th>Status</th><th class='left'>Source</th><th>Refreshed</th>
            </tr></thead>
            <tbody>{rows}</tbody>
           </table>""",
        caption=f"{len(sub)} latest runs",
    )

section_label("Failed Tickers")
if failed_df.empty:
    info_block("No failed tickers logged in the current dataset.")
else:
    sub = failed_df.head(100).copy()
    if "failed_at" in sub.columns:
        sub["failed_at"] = pd.to_datetime(sub["failed_at"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M")
    rows = ""
    for _, r in sub.iterrows():
        rows += (
            "<tr>"
            f"<td class='ticker'>{r.get('ticker','')}</td>"
            f"<td>{r.get('dataset','')}</td>"
            f"<td>{r.get('stage','')}</td>"
            f"<td style='text-align:left;max-width:280px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{r.get('source','')}</td>"
            f"<td style='text-align:left;max-width:420px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{r.get('error_message','')}</td>"
            f"<td>{r.get('failed_at','')}</td>"
            "</tr>"
        )
    table_wrap(
        f"""<table class='trm'>
            <thead><tr>
              <th>Ticker</th><th>Dataset</th><th>Stage</th><th class='left'>Source</th>
              <th class='left'>Error</th><th>Failed At</th>
            </tr></thead>
            <tbody>{rows}</tbody>
           </table>"""
    )

section_label("Operational Notes")
if report.passes:
    info_block(
        "Phase 1 is operational: universe, prices, and returns pass the minimum gate. "
        "The next priority is page rewiring and fundamentals coverage, not more backend breadth."
    )
else:
    warn_block(
        "Phase 1 is not yet fully operational for this universe. Fix the failed rows or missing fundamentals "
        "before trusting downstream analytics."
    )
