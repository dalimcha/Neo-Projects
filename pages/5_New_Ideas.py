from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Ideas Lab — India Terminal",
    layout="wide",
    initial_sidebar_state="expanded",
)

from utils.formatting import inject_css, page_header, section_label, kpi_card, info_block, warn_block, html_block
from utils.data_loader import load_full_universe, load_order_book, load_news, load_filings


inject_css()


PERIOD_RET_MAP = {
    "1M": "return_1m",
    "3M": "return_3m",
    "6M": "return_6m",
    "1Y": "return_1y",
    "3Y": "return_3y",
    "5Y": "return_5y",
    "10Y": "return_10y",
}

PERIOD_QUARTILE_MAP = {
    "1M": "quartile_1m",
    "3M": "quartile_3m",
    "6M": "quartile_6m",
    "1Y": "quartile_1y",
    "3Y": "quartile_3y",
    "5Y": "quartile_5y",
    "10Y": "quartile_10y",
}


@st.cache_data(ttl=300)
def _load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    uni = load_full_universe()
    ob = load_order_book()
    news = load_news()
    filings = load_filings()
    return uni, ob, news, filings


def _safe_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _build_event_flags(df: pd.DataFrame, news_df: pd.DataFrame, filings_df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["has_recent_news"] = False
    out["has_recent_filing"] = False
    out["latest_event"] = pd.NA

    news_map: dict[str, str] = {}
    filing_map: dict[str, str] = {}

    if not news_df.empty and "tickers_mentioned" in news_df.columns:
        tmp = news_df.copy()
        if "date" in tmp.columns:
            tmp = tmp.sort_values("date", ascending=False)
        for _, row in tmp.iterrows():
            tickers = [x.strip().upper() for x in str(row.get("tickers_mentioned", "")).split("|") if x.strip()]
            headline = str(row.get("headline", "")).strip()
            for ticker in tickers:
                if ticker and ticker not in news_map:
                    news_map[ticker] = headline

    if not filings_df.empty and "ticker" in filings_df.columns:
        tmp = filings_df.copy()
        if "date" in tmp.columns:
            tmp = tmp.sort_values("date", ascending=False)
        for _, row in tmp.iterrows():
            ticker = str(row.get("ticker", "")).strip().upper()
            subject = str(row.get("subject", "")).strip()
            if ticker and ticker not in filing_map:
                filing_map[ticker] = subject

    out["has_recent_news"] = out["ticker"].astype(str).str.upper().map(lambda t: t in news_map)
    out["has_recent_filing"] = out["ticker"].astype(str).str.upper().map(lambda t: t in filing_map)
    out["latest_event"] = out["ticker"].astype(str).str.upper().map(
        lambda t: filing_map.get(t) or news_map.get(t) or pd.NA
    )
    return out


def _build_derived_columns(df: pd.DataFrame, ob_df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = _safe_numeric(
        out,
        [
            "pe", "industry_pe", "historical_pe_3y", "historical_pe_5y", "historical_pe_10y",
            "roe", "roce", "debt_equity", "volume_ratio_30d", "dist_52w_high_pct", "dist_52w_low_pct",
            "market_cap_cr", "promoter_holding", "fii_holding", "dii_holding",
            "revenue_growth_1y", "revenue_growth_3y", "revenue_growth_5y",
            "pat_growth_1y", "pat_growth_3y", "pat_growth_5y",
            "ebitda_margin", "current_ratio", "interest_coverage",
        ] + list(PERIOD_RET_MAP.values()),
    )

    for hist_col, label in [("historical_pe_3y", "pe_vs_hist_3y"), ("historical_pe_5y", "pe_vs_hist_5y"), ("historical_pe_10y", "pe_vs_hist_10y")]:
        if hist_col in out.columns and "pe" in out.columns:
            hist = pd.to_numeric(out[hist_col], errors="coerce")
            pe = pd.to_numeric(out["pe"], errors="coerce")
            out[label] = np.where((hist > 0) & pe.notna(), (pe / hist - 1.0) * 100, np.nan)

    if not ob_df.empty:
        ob_cols = [
            "ticker", "ob_revenue_ratio", "ob_marketcap_ratio", "ob_ev_ratio",
            "order_book_cr", "order_inflow_growth_pct", "classification", "confidence_score",
        ]
        ob_keep = [c for c in ob_cols if c in ob_df.columns]
        if ob_keep:
            ob_latest = ob_df[ob_keep].copy().drop_duplicates(subset=["ticker"], keep="last")
            out = out.merge(ob_latest, on="ticker", how="left")

    # Useful ranks / flags
    if "dist_52w_low_pct" in out.columns:
        out["near_52w_low"] = out["dist_52w_low_pct"] <= 10
    if "dist_52w_high_pct" in out.columns:
        out["near_52w_high"] = out["dist_52w_high_pct"] >= -10
    if "volume_ratio_30d" in out.columns:
        out["volume_shock"] = out["volume_ratio_30d"] >= 2
    if "market_cap_cr" in out.columns:
        out["mcap_bucket"] = np.select(
            [out["market_cap_cr"] >= 100000, out["market_cap_cr"] >= 10000],
            ["Large Cap", "Mid Cap"],
            default="Small Cap",
        )
    return out


def _idea_score(df: pd.DataFrame, period_a: str, period_b: str) -> pd.DataFrame:
    out = df.copy()
    score = pd.Series(0.0, index=out.index)
    reasons = pd.Series("", index=out.index, dtype=object)

    qa = PERIOD_QUARTILE_MAP.get(period_a)
    qb = PERIOD_QUARTILE_MAP.get(period_b)
    if qa in out.columns:
        score += np.where(out[qa] == "Q1", 18, np.where(out[qa] == "Q4", 8, 0))
        reasons = np.where(out[qa] == "Q1", reasons + f"{period_a} Q1; ", reasons)
    if qb in out.columns:
        score += np.where(out[qb] == "Q1", 14, np.where(out[qb] == "Q4", 6, 0))
        reasons = np.where(out[qb] == "Q1", reasons + f"{period_b} Q1; ", reasons)

    if "pe_vs_hist_5y" in out.columns:
        pe_gap = pd.to_numeric(out["pe_vs_hist_5y"], errors="coerce")
        score += np.where(pe_gap <= -20, 20, np.where(pe_gap <= 0, 10, 0))
        reasons = np.where(pe_gap <= -20, reasons + "P/E < 5Y avg; ", reasons)

    if "roe" in out.columns:
        roe = pd.to_numeric(out["roe"], errors="coerce")
        score += np.where(roe >= 20, 14, np.where(roe >= 14, 8, 0))
        reasons = np.where(roe >= 20, reasons + "high ROE; ", reasons)

    if "debt_equity" in out.columns:
        de = pd.to_numeric(out["debt_equity"], errors="coerce")
        score += np.where(de <= 0.5, 8, np.where(de <= 1.2, 4, 0))
        reasons = np.where(de <= 0.5, reasons + "clean balance sheet; ", reasons)

    if "dist_52w_low_pct" in out.columns:
        low = pd.to_numeric(out["dist_52w_low_pct"], errors="coerce")
        score += np.where(low <= 10, 10, np.where(low <= 20, 5, 0))
        reasons = np.where(low <= 10, reasons + "near 52W low; ", reasons)

    if "volume_ratio_30d" in out.columns:
        vol = pd.to_numeric(out["volume_ratio_30d"], errors="coerce")
        score += np.where(vol >= 3, 10, np.where(vol >= 1.5, 5, 0))
        reasons = np.where(vol >= 3, reasons + "volume shock; ", reasons)

    if "ob_marketcap_ratio" in out.columns:
        ob_mc = pd.to_numeric(out["ob_marketcap_ratio"], errors="coerce")
        score += np.where(ob_mc >= 1.0, 12, np.where(ob_mc >= 0.75, 6, 0))
        reasons = np.where(ob_mc >= 1.0, reasons + "OB>MCap optional; ", reasons)

    if "has_recent_news" in out.columns and "has_recent_filing" in out.columns:
        evt = out["has_recent_news"].fillna(False) | out["has_recent_filing"].fillna(False)
        score += np.where(evt, 5, 0)
        reasons = np.where(evt, reasons + "recent event; ", reasons)

    out["idea_score"] = score.round(1)
    out["idea_reason"] = pd.Series(reasons, index=out.index).str.rstrip("; ").replace("", "No standout trigger")
    return out


def _signal_buckets(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}

    if {"pe_vs_hist_5y", "roe", "debt_equity"}.issubset(df.columns):
        out["Value Below History"] = df[
            (df["pe_vs_hist_5y"] <= -20)
            & (df["roe"] >= 14)
            & ((df["debt_equity"].isna()) | (df["debt_equity"] <= 1.2))
        ].sort_values(["pe_vs_hist_5y", "roe"], ascending=[True, False])

    if {"quartile_5y", "quartile_3m", "dist_52w_low_pct"}.issubset(df.columns):
        out["Fallen Compounders"] = df[
            (df["quartile_5y"] == "Q1")
            & (df["quartile_3m"].isin(["Q3", "Q4"]))
            & (df["dist_52w_low_pct"] <= 20)
        ].sort_values("dist_52w_low_pct", ascending=True)

    if {"quartile_3y", "quartile_1m", "volume_ratio_30d"}.issubset(df.columns):
        out["Momentum Re-Acceleration"] = df[
            (df["quartile_3y"].isin(["Q1", "Q2"]))
            & (df["quartile_1m"] == "Q1")
            & (df["volume_ratio_30d"] >= 1.5)
        ].sort_values("return_1m", ascending=False)

    if {"ob_marketcap_ratio", "ob_revenue_ratio"}.issubset(df.columns):
        out["Order Book Optional"] = df[
            ((df["ob_marketcap_ratio"] >= 0.75) | (df["ob_revenue_ratio"] >= 2.0))
        ].sort_values(["ob_marketcap_ratio", "ob_revenue_ratio"], ascending=False)

    if {"has_recent_news", "has_recent_filing", "volume_ratio_30d", "return_1d"}.issubset(df.columns):
        out["Event-Backed Movers"] = df[
            (df["has_recent_news"] | df["has_recent_filing"])
            & (df["volume_ratio_30d"] >= 1.5)
            & (df["return_1d"].abs() >= 1.5)
        ].sort_values("return_1d", ascending=False)

    return out


uni_df, ob_df, news_df, filings_df = _load()

page_header(
    "Ideas Lab",
    "Scenario builder for value dislocations, fallen quality, event-backed movers, quartile transitions, and optional special-situation screens.",
)

if uni_df.empty:
    warn_block("No merged universe available. Refresh prices and fundamentals first.")
    st.stop()

df = _build_event_flags(_build_derived_columns(uni_df, ob_df), news_df, filings_df)

with st.sidebar:
    html_block('<div class="sec-label">Idea Filters</div>')
    preset = st.selectbox(
        "Preset",
        [
            "Custom",
            "Value Dislocation",
            "Fallen Compounders",
            "Momentum Re-Acceleration",
            "Event-Backed Movers",
            "Order Book Optional",
        ],
        index=0,
    )
    sectors = ["All"] + sorted(df["sector"].dropna().astype(str).unique().tolist()) if "sector" in df.columns else ["All"]
    sector_f = st.selectbox("Sector", sectors)
    mcap_f = st.selectbox("MCap Bucket", ["All", "Large Cap", "Mid Cap", "Small Cap"])
    only_event = st.checkbox("Only with recent news / filing", value=False)
    only_ob = st.checkbox("Only with order-book data", value=False)

    st.markdown("---")
    period_a = st.selectbox("Period A", list(PERIOD_RET_MAP.keys()), index=3)
    period_b = st.selectbox("Period B", list(PERIOD_RET_MAP.keys()), index=4)
    quartiles = st.multiselect("Quartiles", ["Q1", "Q2", "Q3", "Q4"], default=["Q1", "Q4"])

    st.markdown("---")
    pe_mode = st.selectbox("P/E vs History", ["Any", "Below 3Y Avg", "Below 5Y Avg", "Below 10Y Avg", "Above 3Y Avg", "Above 5Y Avg"])
    near_52 = st.selectbox("52W Position", ["Any", "Near 52W Low", "Near 52W High"])
    min_roe = st.slider("Min ROE %", 0, 40, 12)
    max_de = st.slider("Max Debt/Equity", 0.0, 3.0, 1.5, 0.1)
    min_vol = st.slider("Min Volume Shock", 1.0, 10.0, 1.0, 0.25)

    st.markdown("---")
    ob_mode = st.selectbox("Order Book Signal", ["Any", "OB/MCap > 0.75x", "OB/MCap > 1.0x", "OB/Revenue > 2.0x"])
    min_ret_3y = st.slider("Min 3Y Return %", -100, 400, -100)
    min_ret_10y = st.slider("Min 10Y Return %", -100, 2000, -100)

fdf = df.copy()
if sector_f != "All" and "sector" in fdf.columns:
    fdf = fdf[fdf["sector"] == sector_f]
if mcap_f != "All" and "mcap_bucket" in fdf.columns:
    fdf = fdf[fdf["mcap_bucket"] == mcap_f]
if only_event:
    fdf = fdf[fdf["has_recent_news"] | fdf["has_recent_filing"]]
if only_ob:
    fdf = fdf[fdf["ob_marketcap_ratio"].notna() | fdf["ob_revenue_ratio"].notna()]

qa_col = PERIOD_QUARTILE_MAP[period_a]
qb_col = PERIOD_QUARTILE_MAP[period_b]
if qa_col in fdf.columns:
    fdf = fdf[fdf[qa_col].isin(quartiles)]
if qb_col in fdf.columns:
    fdf = fdf[fdf[qb_col].isin(quartiles)]

if "roe" in fdf.columns:
    fdf = fdf[(fdf["roe"].isna()) | (fdf["roe"] >= min_roe)]
if "debt_equity" in fdf.columns:
    fdf = fdf[(fdf["debt_equity"].isna()) | (fdf["debt_equity"] <= max_de)]
if "volume_ratio_30d" in fdf.columns:
    fdf = fdf[(fdf["volume_ratio_30d"].isna()) | (fdf["volume_ratio_30d"] >= min_vol)]
if "return_3y" in fdf.columns:
    fdf = fdf[(fdf["return_3y"].isna()) | (fdf["return_3y"] >= min_ret_3y)]
if "return_10y" in fdf.columns:
    fdf = fdf[(fdf["return_10y"].isna()) | (fdf["return_10y"] >= min_ret_10y)]

if preset == "Value Dislocation":
    if "pe_vs_hist_5y" in fdf.columns:
        fdf = fdf[fdf["pe_vs_hist_5y"] <= -15]
    if "roe" in fdf.columns:
        fdf = fdf[(fdf["roe"].isna()) | (fdf["roe"] >= 14)]
    if "debt_equity" in fdf.columns:
        fdf = fdf[(fdf["debt_equity"].isna()) | (fdf["debt_equity"] <= 1.2)]
elif preset == "Fallen Compounders":
    if {"quartile_5y", "quartile_3m", "dist_52w_low_pct"}.issubset(fdf.columns):
        fdf = fdf[(fdf["quartile_5y"] == "Q1") & (fdf["quartile_3m"].isin(["Q3", "Q4"])) & (fdf["dist_52w_low_pct"] <= 20)]
elif preset == "Momentum Re-Acceleration":
    if {"quartile_3y", "quartile_1m", "volume_ratio_30d"}.issubset(fdf.columns):
        fdf = fdf[(fdf["quartile_3y"].isin(["Q1", "Q2"])) & (fdf["quartile_1m"] == "Q1") & (fdf["volume_ratio_30d"] >= 1.5)]
elif preset == "Event-Backed Movers":
    if {"has_recent_news", "has_recent_filing", "volume_ratio_30d", "return_1d"}.issubset(fdf.columns):
        fdf = fdf[(fdf["has_recent_news"] | fdf["has_recent_filing"]) & (fdf["volume_ratio_30d"] >= 1.5) & (fdf["return_1d"].abs() >= 0.015)]
elif preset == "Order Book Optional":
    if {"ob_marketcap_ratio", "ob_revenue_ratio"}.issubset(fdf.columns):
        fdf = fdf[(fdf["ob_marketcap_ratio"] >= 0.75) | (fdf["ob_revenue_ratio"] >= 2.0)]

if pe_mode == "Below 3Y Avg" and "pe_vs_hist_3y" in fdf.columns:
    fdf = fdf[fdf["pe_vs_hist_3y"] <= 0]
elif pe_mode == "Below 5Y Avg" and "pe_vs_hist_5y" in fdf.columns:
    fdf = fdf[fdf["pe_vs_hist_5y"] <= 0]
elif pe_mode == "Below 10Y Avg" and "pe_vs_hist_10y" in fdf.columns:
    fdf = fdf[fdf["pe_vs_hist_10y"] <= 0]
elif pe_mode == "Above 3Y Avg" and "pe_vs_hist_3y" in fdf.columns:
    fdf = fdf[fdf["pe_vs_hist_3y"] >= 0]
elif pe_mode == "Above 5Y Avg" and "pe_vs_hist_5y" in fdf.columns:
    fdf = fdf[fdf["pe_vs_hist_5y"] >= 0]

if near_52 == "Near 52W Low" and "dist_52w_low_pct" in fdf.columns:
    fdf = fdf[fdf["dist_52w_low_pct"] <= 10]
elif near_52 == "Near 52W High" and "dist_52w_high_pct" in fdf.columns:
    fdf = fdf[fdf["dist_52w_high_pct"] >= -10]

if ob_mode == "OB/MCap > 0.75x" and "ob_marketcap_ratio" in fdf.columns:
    fdf = fdf[fdf["ob_marketcap_ratio"] >= 0.75]
elif ob_mode == "OB/MCap > 1.0x" and "ob_marketcap_ratio" in fdf.columns:
    fdf = fdf[fdf["ob_marketcap_ratio"] >= 1.0]
elif ob_mode == "OB/Revenue > 2.0x" and "ob_revenue_ratio" in fdf.columns:
    fdf = fdf[fdf["ob_revenue_ratio"] >= 2.0]

fdf = _idea_score(fdf, period_a, period_b)
if "idea_score" in fdf.columns:
    fdf = fdf.sort_values(["idea_score", "return_3m"], ascending=[False, False], na_position="last")

html_block(
    """
    <div class="hero-panel">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap;">
        <div>
          <div class="hero-kicker">Ideas Lab</div>
          <div class="hero-title">Multi-Metric Scenario Builder</div>
          <div class="hero-sub">Experiment across valuation, quartiles, 52-week positioning, event catalysts, balance sheet quality, and optional order-book signals over multiple time horizons.</div>
        </div>
      </div>
    </div>
    """
)

cols = st.columns(5)
with cols[0]:
    kpi_card("Candidates", str(len(fdf)), "after filters")
with cols[1]:
    kpi_card("With P/E History", str(int(fdf.get("historical_pe_5y", pd.Series(dtype=float)).notna().sum())), "5Y baseline")
with cols[2]:
    kpi_card("Event-backed", str(int((fdf.get("has_recent_news", False) | fdf.get("has_recent_filing", False)).sum())), "news / filing")
with cols[3]:
    kpi_card("Near 52W Lows", str(int(fdf.get("near_52w_low", pd.Series(dtype=bool)).fillna(False).sum())), "<= 10%")
with cols[4]:
    kpi_card("OB Optional", str(int(fdf.get("ob_marketcap_ratio", pd.Series(dtype=float)).notna().sum())), "coverage")
with st.container():
    top_ideas = fdf.head(5) if "idea_score" in fdf.columns else pd.DataFrame()
    if not top_ideas.empty:
        section_label("Highest-Scoring Setups")
        for _, row in top_ideas.iterrows():
            info_block(
                f"{row.get('ticker','')} · {row.get('company_name','')} · Score {row.get('idea_score','—')} "
                f"· {row.get('idea_reason','No standout trigger')}"
            )

section_label("Scenario Summary")
summary_cols = st.columns(4)
with summary_cols[0]:
    q1_5y = int((fdf.get("quartile_5y", pd.Series(dtype=object)) == "Q1").sum())
    kpi_card("5Y Q1", str(q1_5y), "durable winners")
with summary_cols[1]:
    cheap = int((pd.to_numeric(fdf.get("pe_vs_hist_5y"), errors="coerce") <= -20).sum()) if "pe_vs_hist_5y" in fdf.columns else 0
    kpi_card("Cheap vs 5Y", str(cheap), "P/E below history")
with summary_cols[2]:
    compounders = int(((fdf.get("quartile_5y") == "Q1") & (fdf.get("quartile_3m").isin(["Q3", "Q4"]))).sum()) if {"quartile_5y", "quartile_3m"}.issubset(fdf.columns) else 0
    kpi_card("Fallen Quality", str(compounders), "Q1 long-term, weak short-term")
with summary_cols[3]:
    event_count = int((fdf.get("has_recent_news", False) | fdf.get("has_recent_filing", False)).sum())
    kpi_card("Event-Linked", str(event_count), "fresh catalyst")

section_label("Quartile Crosstab")
if qa_col in df.columns and qb_col in df.columns:
    ctab = (
        df.dropna(subset=[qa_col, qb_col])
        .groupby([qa_col, qb_col]).size()
        .unstack(fill_value=0)
        .reindex(index=["Q1", "Q2", "Q3", "Q4"], columns=["Q1", "Q2", "Q3", "Q4"], fill_value=0)
    )
    st.dataframe(ctab, width="stretch")
else:
    info_block("Quartile crosstab will populate after the returns snapshot has quartile columns.")

section_label("Transitions")
if qa_col in df.columns and qb_col in df.columns:
    up = fdf[(fdf[qa_col] == "Q4") & (fdf[qb_col] == "Q1")].head(5)
    down = fdf[(fdf[qa_col] == "Q1") & (fdf[qb_col] == "Q4")].head(5)
    c1, c2 = st.columns(2)
    with c1:
        info_block(
            f"Q4 → Q1 ({period_a} vs {period_b}): " +
            (", ".join(up["ticker"].astype(str).tolist()) if not up.empty else "None")
        )
    with c2:
        info_block(
            f"Q1 → Q4 ({period_a} vs {period_b}): " +
            (", ".join(down["ticker"].astype(str).tolist()) if not down.empty else "None")
        )

section_label("Signal Buckets")
signals = _signal_buckets(fdf)
if not signals:
    info_block("No signal buckets available under the current filters.")
else:
    grid_cols = st.columns(3)
    for idx, (name, sub) in enumerate(signals.items()):
        with grid_cols[idx % 3]:
            top = sub.head(5)
            summary = ", ".join(top["ticker"].astype(str).tolist()) if not top.empty else "No candidates"
            kpi_card(name, str(len(sub)), summary)

section_label("Idea Candidates")
display_cols = [
    "ticker", "company_name", "sector", "industry", "price",
    "return_1m", "return_3m", "return_1y", "return_3y", "return_5y", "return_10y",
    qa_col, qb_col, "pe", "historical_pe_5y", "pe_vs_hist_5y",
    "roe", "roce", "debt_equity", "dist_52w_high_pct", "dist_52w_low_pct",
    "volume_ratio_30d", "ob_marketcap_ratio", "ob_revenue_ratio", "latest_event",
    "idea_score", "idea_reason",
]
display_cols = [c for c in display_cols if c in fdf.columns]
table_df = fdf[display_cols].copy().sort_values(
    by=[qb_col if qb_col in fdf.columns else "ticker", "return_3m" if "return_3m" in fdf.columns else "ticker"],
    ascending=[True, False],
    na_position="last",
)
table_df = table_df.rename(columns={
    "ticker": "Ticker",
    "company_name": "Company",
    "sector": "Sector",
    "industry": "Industry",
    "price": "Price",
    "return_1m": "1M %",
    "return_3m": "3M %",
    "return_1y": "1Y %",
    "return_3y": "3Y %",
    "return_5y": "5Y %",
    "return_10y": "10Y %",
    qa_col: f"Q {period_a}",
    qb_col: f"Q {period_b}",
    "pe": "P/E",
    "historical_pe_5y": "Hist PE 5Y",
    "pe_vs_hist_5y": "P/E vs 5Y %",
    "roe": "ROE %",
    "roce": "ROCE %",
    "debt_equity": "D/E",
    "dist_52w_high_pct": "52W High Dist %",
    "dist_52w_low_pct": "52W Low Dist %",
    "volume_ratio_30d": "Vol/30D",
    "ob_marketcap_ratio": "OB/MCap",
    "ob_revenue_ratio": "OB/Rev",
    "latest_event": "Latest Event",
    "idea_score": "Idea Score",
    "idea_reason": "Why It Surfaced",
})

if table_df.empty:
    warn_block("No companies match the current screen. Relax one or two filters and re-run the idea set.")
else:
    st.dataframe(
        table_df,
        hide_index=True,
        width="stretch",
        height=760,
        column_config={
            "Price": st.column_config.NumberColumn(format="₹ %.2f"),
            "1M %": st.column_config.NumberColumn(format="%.1f%%"),
            "3M %": st.column_config.NumberColumn(format="%.1f%%"),
            "1Y %": st.column_config.NumberColumn(format="%.1f%%"),
            "3Y %": st.column_config.NumberColumn(format="%.1f%%"),
            "5Y %": st.column_config.NumberColumn(format="%.1f%%"),
            "10Y %": st.column_config.NumberColumn(format="%.1f%%"),
            "P/E": st.column_config.NumberColumn(format="%.1f"),
            "Hist PE 5Y": st.column_config.NumberColumn(format="%.1f"),
            "P/E vs 5Y %": st.column_config.NumberColumn(format="%.1f%%"),
            "ROE %": st.column_config.NumberColumn(format="%.1f%%"),
            "ROCE %": st.column_config.NumberColumn(format="%.1f%%"),
            "D/E": st.column_config.NumberColumn(format="%.2f"),
            "52W High Dist %": st.column_config.NumberColumn(format="%.1f%%"),
            "52W Low Dist %": st.column_config.NumberColumn(format="%.1f%%"),
            "Vol/30D": st.column_config.NumberColumn(format="%.2fx"),
            "OB/MCap": st.column_config.NumberColumn(format="%.2fx"),
            "OB/Rev": st.column_config.NumberColumn(format="%.2fx"),
            "Idea Score": st.column_config.NumberColumn(format="%.1f"),
        },
    )
    st.download_button(
        "Export Idea Set CSV",
        data=table_df.to_csv(index=False),
        file_name="idea_lab_candidates.csv",
        mime="text/csv",
    )

section_label("How To Use")
info_block(
    "Use quartiles to compare long-duration winners against short-term weakness. "
    "Typical high-signal setups are Q1 on 5Y with Q4 on 3M, or current P/E trading below 5Y average "
    "while ROE remains healthy. Order-book metrics are optional and only apply where source data exists."
)
