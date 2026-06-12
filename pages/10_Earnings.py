from __future__ import annotations

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Earnings — India Terminal",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.formatting import inject_css, page_header, section_label, info_block, kpi_card, html_block
from utils.data_loader import load_quarterly, load_results_calendar, load_full_universe, load_fundamentals


inject_css()


@st.cache_data(ttl=300)
def _load():
    return load_quarterly(), load_results_calendar(), load_full_universe(), load_fundamentals()


def _quarter_sort_key(q: str) -> tuple[int, int]:
    q = str(q).upper().strip()
    if len(q) < 2:
        return (0, 0)
    try:
        return (int(q[-2:]), int(q[1]))
    except Exception:
        return (0, 0)


qdf, cal_df, uni_df, fund_df = _load()

page_header("", "")

if qdf.empty and cal_df.empty:
    info_block("No quarterly financials or results calendar available yet.")
    st.stop()

html_block(
    """
    <div class="hero-panel">
      <div class="hero-sub" style="text-transform:uppercase;letter-spacing:0.10em;font-size:0.62rem;">Earnings</div>
      <div class="hero-title">Reporting Calendar and Beat / Miss Tracker</div>
    </div>
    """
)

today = pd.Timestamp.today().normalize()

section_label("Upcoming 7 Days")
if cal_df.empty:
    info_block("No results calendar loaded. Add data/results_calendar.csv with ticker, expected_date, board_meeting_date, status.")
else:
    upcoming = cal_df.copy()
    if "expected_date" in upcoming.columns:
        upcoming = upcoming[(upcoming["expected_date"] >= today) & (upcoming["expected_date"] <= today + pd.Timedelta(days=7))]
    if not uni_df.empty and "index_membership" in uni_df.columns:
        allowed = set(uni_df[uni_df["index_membership"].astype(str).str.contains("Nifty500", na=False)]["ticker"])
        upcoming = upcoming[upcoming["ticker"].isin(allowed)]
    st.dataframe(upcoming, hide_index=True, width="stretch", height=260)


def _reported_week_table(q: pd.DataFrame) -> pd.DataFrame:
    if q.empty:
        return pd.DataFrame()
    x = q.copy()
    x["period_end"] = pd.to_datetime(x["period_end"], errors="coerce")
    x = x.dropna(subset=["period_end"]).sort_values(["ticker", "period_end"])
    latest = x.groupby("ticker", as_index=False).last()
    latest = latest[latest["period_end"] >= (today - pd.Timedelta(days=7))]
    rows = []
    for _, row in latest.iterrows():
        ticker = row["ticker"]
        hist = x[x["ticker"] == ticker].tail(5)
        trailing = hist.iloc[:-1]
        rev_avg = trailing["revenue_cr"].mean() if "revenue_cr" in trailing.columns and not trailing.empty else pd.NA
        ebitda_avg = trailing["ebitda_cr"].mean() if "ebitda_cr" in trailing.columns and not trailing.empty else pd.NA
        rev = pd.to_numeric(row.get("revenue_cr"), errors="coerce")
        ebitda = pd.to_numeric(row.get("ebitda_cr"), errors="coerce")
        rev_delta = ((rev / rev_avg) - 1) * 100 if pd.notna(rev) and pd.notna(rev_avg) and rev_avg else pd.NA
        ebitda_delta = ((ebitda / ebitda_avg) - 1) * 100 if pd.notna(ebitda) and pd.notna(ebitda_avg) and ebitda_avg else pd.NA
        comment = "No trailing baseline."
        if pd.notna(rev_delta):
            direction = "accelerating" if rev_delta > 5 else ("softening" if rev_delta < -5 else "steady")
            comment = f"Revenue {rev_delta:+.1f}% vs trailing 4-quarter avg — {direction}."
        rows.append({
            "Ticker": ticker,
            "Fiscal Year": row.get("fiscal_year"),
            "Quarter": row.get("quarter"),
            "Period End": row.get("period_end"),
            "Revenue (Cr)": rev,
            "EBITDA (Cr)": ebitda,
            "Revenue vs 4Q Avg %": rev_delta,
            "EBITDA vs 4Q Avg %": ebitda_delta,
            "Auto Comment": comment,
        })
    return pd.DataFrame(rows)


section_label("Reported This Week")
reported = _reported_week_table(qdf)
if reported.empty:
    info_block("No fresh quarterly reports found in the last 7 days from the loaded quarterly dataset.")
else:
    st.dataframe(
        reported.sort_values("Period End", ascending=False),
        hide_index=True,
        width="stretch",
        height=360,
        column_config={
            "Revenue (Cr)": st.column_config.NumberColumn(format="₹ %.0f"),
            "EBITDA (Cr)": st.column_config.NumberColumn(format="₹ %.0f"),
            "Revenue vs 4Q Avg %": st.column_config.NumberColumn(format="%.1f%%"),
            "EBITDA vs 4Q Avg %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

section_label("Latest Result Coverage")
if fund_df.empty:
    info_block("No fundamentals file available.")
else:
    coverage = fund_df.copy()
    if "latest_result_date" in coverage.columns:
        coverage["latest_result_date"] = pd.to_datetime(coverage["latest_result_date"], errors="coerce")
    k1, k2, k3 = st.columns(3)
    with k1:
        kpi_card("Tickers", str(len(coverage)), "fundamentals rows")
    with k2:
        kpi_card("With Result Date", str(int(coverage["latest_result_date"].notna().sum())) if "latest_result_date" in coverage.columns else "0", "known latest result")
    with k3:
        kpi_card("Quarterly Rows", str(len(qdf)), "loaded quarterly records")
