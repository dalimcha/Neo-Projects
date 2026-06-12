"""
Special Situations
──────────────────
Optional signal surface for order-book-heavy names and source-traceable
special situations. This is no longer presented as the core product.
"""

import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Special Situations — India Terminal",
    layout="wide", initial_sidebar_state="expanded",
)

from utils.formatting import (
    inject_css, page_header, section_label, kpi_card, fmt_pct, fmt_cr,
    fmt_ratio, info_block, warn_block, ok_block, ai_box, badge_html,
    score_bar, table_wrap,
    POS, NEG, ACCENT, TEXT3, BG2, BORDER,
)
from utils.data_loader import load_order_book, save_order_book
from utils.scoring import (
    score_order_book_df, calculate_ob_score, FACTOR_LABELS, FACTOR_MAX,
    CLASSIFICATION_ORDER,
)
from utils.charting import (
    ob_score_scatter, classification_donut, ob_score_breakdown, _empty_chart,
)
import utils.ai_summarizer as ai

inject_css()

# ── Load & score data ─────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def _scored():
    ob = load_order_book()
    if ob.empty:
        return ob
    return score_order_book_df(ob)

df = _scored()

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sec-label">Filters</div>', unsafe_allow_html=True)

    cls_filter = st.multiselect(
        "Classification",
        CLASSIFICATION_ORDER,
        default=["High Conviction Idea", "Watchlist Add", "Needs More Research"],
    )

    if not df.empty and "sector" in df.columns:
        sectors = ["All"] + sorted(df["sector"].dropna().unique().tolist())
    else:
        sectors = ["All"]
    sector_f = st.selectbox("Sector", sectors)

    min_score = st.slider("Minimum OB Score", 0, 100, 0)
    min_ob_rev = st.slider("Min OB / Revenue ratio", 0.0, 10.0, 0.0, 0.5)

    st.markdown("---")
    verified_only = st.checkbox("Manually Verified Only", value=False)

    st.markdown("---")
    st.markdown('<div class="sec-label">Actions</div>', unsafe_allow_html=True)
    add_new = st.checkbox("Add New Company")

page_header(
    "Special Situations",
    f"{len(df)} optional signal rows",
)

if df.empty:
    warn_block(
        "Order book database is empty. "
        "Add companies to data/order_book.csv or use the form below."
    )

# ── Apply filters ─────────────────────────────────────────────────────────────
fdf = df.copy()
if not fdf.empty:
    if cls_filter and "classification" in fdf.columns:
        fdf = fdf[fdf["classification"].isin(cls_filter)]
    if sector_f != "All" and "sector" in fdf.columns:
        fdf = fdf[fdf["sector"] == sector_f]
    if "ob_score" in fdf.columns:
        fdf = fdf[fdf["ob_score"] >= min_score]
    if "ob_revenue_ratio" in fdf.columns:
        fdf = fdf[fdf["ob_revenue_ratio"] >= min_ob_rev]
    if verified_only and "manually_verified" in fdf.columns:
        fdf = fdf[fdf["manually_verified"] == True]

# ── Summary KPIs ──────────────────────────────────────────────────────────────
section_label("Portfolio Overview")

kpi_cols = st.columns(5)
if not df.empty:
    high_conv = (df.get("classification", pd.Series()) == "High Conviction Idea").sum()
    watchlist = (df.get("classification", pd.Series()) == "Watchlist Add").sum()
    avg_score = df.get("ob_score", pd.Series(dtype=float)).mean()
    avg_ob_rev = df.get("ob_revenue_ratio", pd.Series(dtype=float)).mean()
    n_verified = df.get("manually_verified", pd.Series(dtype=bool)).sum() if "manually_verified" in df.columns else 0
else:
    high_conv = watchlist = avg_score = avg_ob_rev = n_verified = 0

kpi_data = [
    ("High Conviction", str(high_conv), ""),
    ("Watchlist",       str(watchlist), ""),
    ("Avg OB Score",    f"{avg_score:.1f}/100" if avg_score else "—", ""),
    ("Avg OB/Rev",      f"{avg_ob_rev:.1f}x" if avg_ob_rev else "—", ""),
    ("Verified Data",   str(n_verified), f"of {len(df)} total"),
]
for col, (lbl, val, sub) in zip(kpi_cols, kpi_data):
    with col:
        kpi_card(lbl, val, sub)

st.markdown("<br>", unsafe_allow_html=True)

# ── Charts ────────────────────────────────────────────────────────────────────
col_a, col_b = st.columns([3, 2])
with col_a:
    section_label("Score vs OB/Revenue Ratio")
    if not df.empty:
        fig = ob_score_scatter(df)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.plotly_chart(_empty_chart("No data"), use_container_width=True)

with col_b:
    section_label("Classification Breakdown")
    if not df.empty:
        fig = classification_donut(df)
        st.plotly_chart(fig, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Master leaderboard ────────────────────────────────────────────────────────
section_label(f"Special Situations Leaderboard — {len(fdf)} companies")

if not fdf.empty:
    # Render table
    COLS = [
        "ticker","company_name","sector",
        "ob_score","classification",
        "order_book_cr","ob_revenue_ratio","ob_marketcap_ratio",
        "revenue_growth_pct","ebitda_margin_pct","ebitda_margin_trend",
        "debt_equity","confidence_score","manually_verified",
    ]
    show_cols = [c for c in COLS if c in fdf.columns]
    tbl = fdf[show_cols].copy()

    rows = ""
    for _, r in tbl.iterrows():
        score = r.get("ob_score", 0) or 0
        sc_html = score_bar(score, width=80)
        cls = r.get("classification", "")
        bdg = badge_html(cls) if cls else ""
        is_verified = str(r.get("manually_verified", "")).lower() in ("true", "1", "yes")
        verified = (
            '<span style="color:#16a34a;font-size:0.7rem;font-weight:600;">&#10003; Verified</span>'
            if is_verified else
            '<span style="color:#d97706;font-size:0.68rem;">&#9711; Unverified</span>'
        )
        conf = r.get("confidence_score", 0) or 0
        conf_col = "#22c55e" if conf >= 85 else ("#3b82f6" if conf >= 75 else "#f59e0b")
        margin_t = str(r.get("ebitda_margin_trend", ""))
        mt_col = "#22c55e" if "improv" in margin_t.lower() else (
                 "#ef4444" if "decl" in margin_t.lower() else "#3d5270")
        rev_gr = r.get("revenue_growth_pct") or 0
        rows += (
            f"<tr>"
            f"<td class='ticker'>{r.get('ticker','')}</td>"
            f"<td class='name'>{r.get('company_name','')}</td>"
            f"<td style='text-align:left;color:#3d5270;font-size:0.71rem;'>{r.get('sector','')}</td>"
            f"<td>{sc_html}</td>"
            f"<td style='text-align:left;'>{bdg}</td>"
            f"<td style='color:#94a3b8;'>{fmt_cr(r.get('order_book_cr',''))}</td>"
            f"<td style='color:#e2e8f0;font-weight:500;'>{fmt_ratio(r.get('ob_revenue_ratio',''))}</td>"
            f"<td>{fmt_ratio(r.get('ob_marketcap_ratio',''))}</td>"
            f"<td class='{'pos' if rev_gr > 0 else ('neg' if rev_gr < 0 else 'neu')}'>"
            f"{fmt_pct(rev_gr)}</td>"
            f"<td style='color:#94a3b8;'>{fmt_pct(r.get('ebitda_margin_pct',''))}</td>"
            f"<td style='color:{mt_col};font-size:0.69rem;'>{margin_t}</td>"
            f"<td>{fmt_ratio(r.get('debt_equity',''))}</td>"
            f"<td style='color:{conf_col};font-family:\"IBM Plex Mono\",monospace;font-weight:600;'>{conf:.0f}</td>"
            f"<td>{verified}</td>"
            f"</tr>"
        )

    table_wrap(
        f"""<table class='trm'>
            <thead><tr>
              <th class='left'>Ticker</th>
              <th class='left'>Company</th>
              <th class='left'>Sector</th>
              <th class='left'>Score</th>
              <th class='left'>Classification</th>
              <th>Order Book</th>
              <th>OB/Rev</th>
              <th>OB/MCap</th>
              <th>Rev Gr %</th>
              <th>EBITDA Mg</th>
              <th>Margin Trend</th>
              <th>D/E</th>
              <th>Conf</th>
              <th>Verified</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>""",
        caption=f"{len(fdf)} companies",
        caption_right="Sorted by OB Score (descending)",
    )

    # Export
    csv = fdf.to_csv(index=False)
    st.download_button(
        "Export Screener Results",
        data=csv,
        file_name=f"ob_screener_{pd.Timestamp.today().date()}.csv",
        mime="text/csv",
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Individual company deep-dive ──────────────────────────────────────────────
section_label("Company Score Breakdown")

if not df.empty:
    sel_ticker = st.selectbox(
        "Select company for score breakdown",
        df["ticker"].tolist() if "ticker" in df.columns else [],
    )
    if sel_ticker:
        row = df[df["ticker"] == sel_ticker].iloc[0]
        result = calculate_ob_score(row)
        score  = result["ob_score"]
        cls    = result["classification"]

        col1, col2, col3 = st.columns([1, 2, 2])
        with col1:
            kpi_card("OB Score", f"{score:.0f}/100", cls)
            st.markdown(
                f'<div style="margin-top:0.5rem;">{badge_html(cls)}</div>',
                unsafe_allow_html=True,
            )

        with col2:
            section_label("Factor Breakdown")
            fig = ob_score_breakdown(result["factors"], FACTOR_MAX, sel_ticker)
            st.plotly_chart(fig, use_container_width=True)

        with col3:
            section_label("Factor Details")
            for factor, pts in result["factors"].items():
                max_pts = FACTOR_MAX[factor]
                label = FACTOR_LABELS[factor]
                pct = pts / max_pts * 100
                st.markdown(
                    f'<div style="margin-bottom:0.4rem;">'
                    f'<div style="display:flex;justify-content:space-between;'
                    f'font-size:0.72rem;margin-bottom:0.15rem;">'
                    f'<span style="color:#94a3b8;">{label}</span>'
                    f'<span style="color:#e2e8f0;font-family:\'IBM Plex Mono\',monospace;">'
                    f'{pts:.1f}/{max_pts}</span></div>'
                    f'<div class="score-bar-wrap">'
                    f'<div class="score-bar-fill" style="width:{pct}%;background:#3b82f6;"></div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

            if result["penalties"]:
                section_label("Penalties Applied")
                for p in result["penalties"]:
                    st.markdown(
                        f'<div style="font-size:0.74rem;color:#ef4444;'
                        f'padding:0.2rem 0;border-bottom:1px solid #1a2840;">'
                        f'— {p}</div>',
                        unsafe_allow_html=True,
                    )

        # Source traceability
        section_label("Data Source Traceability")
        src_cols = st.columns(4)
        src_data = [
            ("Source Document", str(row.get("source_document", "—"))),
            ("Source Date",     str(row.get("source_date", "—"))[:10]),
            ("Confidence Score", f"{row.get('confidence_score', 0):.0f}/100"),
            ("Verified",        "Yes" if row.get("manually_verified") else "No — requires verification"),
        ]
        for col, (k, v) in zip(src_cols, src_data):
            with col:
                kpi_card(k, v)

        snippet = row.get("extracted_text", "")
        if snippet:
            ai_box(snippet, "Extracted Source Text")

# ── Data Entry Form ───────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
section_label("Scoring Model Reference")

with st.expander("View scoring methodology"):
    st.markdown(
        """**6-Factor Optional Order-Book Signal Score (0–100)**

| Factor | Weight | What it measures |
|--------|--------|-----------------|
| Order Book / Revenue | 30% | Revenue visibility (OB > 3x = strong) |
| Order Inflow Growth | 20% | Whether new orders are accelerating |
| Revenue Growth | 15% | Actual execution pace |
| Margin Stability | 15% | EBITDA margin trend (improving/stable/declining) |
| Valuation vs Peers | 10% | EV/EBITDA discount to sector |
| Balance Sheet Quality | 10% | D/E, working capital days, CFO conversion |

**Penalties deducted for:**
- Receivables growing >8pp faster than revenue → −6 pts
- Falling EBITDA margins → −12 pts
- High debt (D/E > 2x) → −8 pts
- Slow execution cycle (>36 months) → −6 pts
- Weak CFO/PAT conversion (<50%) → −6 pts
- One-off orders (manual flag) → −10 pts
- Customer concentration (manual flag) → −6 pts

**Classification thresholds:**
- **High Conviction Idea**: Score ≥ 72
- **Watchlist Add**: Score ≥ 58
- **Needs More Research**: Score ≥ 42
- **Momentum But Expensive**: Good OB + high PE premium
- **Value Trap**: Cheap PE + falling margins / weak cash flow
- **Avoid**: Score < 42 with no mitigating factors
""",
        unsafe_allow_html=False,
    )

# ── Add / Edit form ───────────────────────────────────────────────────────────
if add_new:
    st.markdown("<br>", unsafe_allow_html=True)
    section_label("Add New Company to Special Situations Database")

    warn_block(
        "IMPORTANT: Do not enter order book data without a verified source document. "
        "Every entry must have a source document, source date, and extracted text snippet."
    )

    with st.form("add_ob_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            f_ticker  = st.text_input("Ticker (NSE Symbol)*")
            f_company = st.text_input("Company Name*")
            f_sector  = st.text_input("Sector")
            f_mcap    = st.number_input("Market Cap (Cr)", min_value=0.0)
            f_ev      = st.number_input("Enterprise Value (Cr)", min_value=0.0)
        with col2:
            f_rev_ttm = st.number_input("TTM Revenue (Cr)*", min_value=0.0)
            f_ob      = st.number_input("Order Book (Cr)*", min_value=0.0)
            f_inflow  = st.number_input("Order Inflow (Cr, last 12M)", min_value=0.0)
            f_inflow_g = st.number_input("Inflow Growth YoY %", value=0.0)
            f_rev_g   = st.number_input("Revenue Growth %", value=0.0)
        with col3:
            f_ebitda_mg = st.number_input("EBITDA Margin %", min_value=0.0, max_value=100.0)
            f_margin_t  = st.selectbox("Margin Trend", ["stable","improving","slightly_declining","declining"])
            f_de        = st.number_input("Debt/Equity", min_value=0.0, value=0.0)
            f_wc_days   = st.number_input("Working Capital Days", min_value=0, value=90)
            f_exec_cy   = st.number_input("Execution Cycle (months)", min_value=0, value=24)

        col4, col5 = st.columns(2)
        with col4:
            f_source_doc  = st.text_input("Source Document*", placeholder="Q3FY25 Earnings Call Transcript")
            f_source_date = st.date_input("Source Date*")
            f_conf        = st.slider("Confidence Score (0=uncertain, 100=exact quote)", 0, 100, 70)
        with col5:
            f_snippet     = st.text_area("Extracted Text Snippet*", height=100,
                                          placeholder="Paste verbatim quote from source document…")
            f_mgmt        = st.text_area("Management Commentary", height=100)

        f_one_off  = st.checkbox("One-off order (penalises score)")
        f_cust_con = st.checkbox("Customer concentration risk")
        f_verified = st.checkbox("I have manually verified this data against the source")

        submitted = st.form_submit_button("Add to Database")

        if submitted:
            if not f_ticker or not f_company or not f_rev_ttm or not f_ob or not f_source_doc or not f_snippet:
                st.error("Fields marked * are required. Source document and extracted text are mandatory.")
            elif not f_verified:
                st.error("You must confirm manual verification before adding data.")
            else:
                ob_rev = f_ob / f_rev_ttm if f_rev_ttm > 0 else 0
                ob_mc  = f_ob / f_mcap    if f_mcap > 0  else 0
                ob_ev  = f_ob / f_ev      if f_ev > 0    else 0
                btb    = f_inflow / f_rev_ttm if f_rev_ttm > 0 else 0

                new_row = {
                    "ticker": f_ticker.upper(), "company_name": f_company,
                    "sector": f_sector, "market_cap_cr": f_mcap, "ev_cr": f_ev,
                    "ttm_revenue_cr": f_rev_ttm, "annual_revenue_cr": f_rev_ttm,
                    "order_book_cr": f_ob, "order_inflow_cr": f_inflow,
                    "order_inflow_growth_pct": f_inflow_g,
                    "ob_revenue_ratio": round(ob_rev, 2),
                    "ob_marketcap_ratio": round(ob_mc, 2),
                    "ob_ev_ratio": round(ob_ev, 2),
                    "btb_ratio": round(btb, 2),
                    "revenue_growth_pct": f_rev_g,
                    "ebitda_margin_pct": f_ebitda_mg,
                    "ebitda_margin_trend": f_margin_t,
                    "debt_equity": f_de,
                    "working_capital_days": f_wc_days,
                    "execution_cycle_months": f_exec_cy,
                    "one_off_order": f_one_off,
                    "customer_concentration": f_cust_con,
                    "management_commentary": f_mgmt,
                    "source_document": f_source_doc,
                    "source_date": str(f_source_date),
                    "extracted_text": f_snippet,
                    "confidence_score": f_conf,
                    "manually_verified": f_verified,
                    "last_updated": str(pd.Timestamp.today().date()),
                }

                existing = load_order_book()
                # Remove existing row for same ticker if present
                if not existing.empty and "ticker" in existing.columns:
                    existing = existing[existing["ticker"] != f_ticker.upper()]
                new_df = pd.concat([existing, pd.DataFrame([new_row])], ignore_index=True)
                save_order_book(new_df)
                ok_block(f"{f_ticker.upper()} added to order book database.")
                st.rerun()
