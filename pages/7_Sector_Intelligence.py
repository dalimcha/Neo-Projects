"""
Sector Intelligence
───────────────────
Deep-dive pages for each sector: cycle, drivers, valuation, mispricing candidates.
"""

import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Sector Intelligence — India Terminal",
    layout="wide", initial_sidebar_state="expanded",
)

from utils.formatting import (
    inject_css, page_header, section_label, kpi_card, fmt_pct,
    fmt_cr, fmt_ratio, info_block, ai_box, table_wrap, badge_html,
    ACCENT, POS, NEG, TEXT3, BG2,
)
from utils.data_loader import load_sectors, load_full_universe, load_order_book, load_news
from utils.scoring import score_order_book_df
from utils.charting import sector_heatmap, peer_comparison_bar

inject_css()

# ── Static sector intelligence ────────────────────────────────────────────────
SECTOR_INTEL = {
    "Capital Goods": {
        "tagline": "Engineering, defence, EPC — riding the government capex supercycle",
        "cycle": "Early-to-Mid Upcycle",
        "cycle_note": (
            "India's government capex at multi-decade highs (Rs 11.1 lakh crore in FY26 budget). "
            "Defence indigenisation under Atmanirbhar Bharat driving 3-5 year order visibility. "
            "Private capex starting to revive in select sectors."
        ),
        "demand_drivers": [
            "Government infrastructure spending — railways, roads, defence, ports",
            "Defence indigenisation: 75% procurement from domestic industry target",
            "Power sector T&D upgrade — Rs 3.5 lakh crore RDSS/TBCB investment",
            "Renewable energy — 500 GW target by 2030",
            "PLI schemes driving electronics manufacturing (EMS)",
        ],
        "margin_drivers": [
            "Operating leverage as revenue scales from growing order books",
            "Project mix improving (defence > infra, better margins)",
            "Cost normalisation (steel, cement inputs easing)",
            "Working capital efficiency as execution pace improves",
        ],
        "risks": [
            "Execution slippage in large projects (L&T, BHEL)",
            "Rising receivables from government customers",
            "Input cost inflation (steel, aluminium, copper)",
            "Competition intensifying in EMS segment (Dixon, Kaynes)",
            "Dependence on government budget allocations",
        ],
        "quality_cos": ["L&T", "HAL", "BEL", "SIEMENS", "ABB", "THERMAX"],
        "momentum_cos": ["HAL", "MAZDOCK", "GRSE", "RVNL", "DATAPATT", "ZENTEC"],
        "mispricing_candidates": ["IRCON", "RVNL", "KPIL", "KEC", "TITAGARH", "ITD"],
        "valuation_note": (
            "Sector median EV/EBITDA ~25-35x. High-quality defence names (HAL, BEL, MAZDOCK) "
            "trade at 35-50x. EPC companies (RVNL, IRCON, KEC) at 15-25x. "
            "EMS (Dixon, Kaynes) at 35-50x despite low margins due to growth premium."
        ),
    },
    "Power": {
        "tagline": "The structural story — renewable build-out + T&D upgrade + data centre demand",
        "cycle": "Mid Upcycle",
        "cycle_note": (
            "Power demand growing at 7-8% CAGR driven by industrial, cooling, and EV loads. "
            "500 GW renewables target by 2030 requires massive grid upgrade. "
            "Rs 3.5 lakh crore RDSS + PM-Surya Ghar driving distribution capex."
        ),
        "demand_drivers": [
            "Renewable energy capacity addition (70-80 GW/year target)",
            "Power distribution upgrade (RDSS scheme)",
            "Grid-scale battery storage investments",
            "Data centre power demand growing 30%+ annually",
            "EV charging infrastructure rollout",
        ],
        "margin_drivers": [
            "Pass-through tariff structures for regulated utilities",
            "Module cost deflation benefiting solar project economics",
            "Long-term PPAs providing revenue visibility",
        ],
        "risks": [
            "Curtailment risk for renewable energy",
            "Equipment price volatility (solar panels, transformers)",
            "Financing costs for large capacity projects",
            "Regulatory risk on tariff revisions",
        ],
        "quality_cos": ["POWERGRID", "NTPC", "TATAPOWER"],
        "momentum_cos": ["ADANIGREEN", "ADANIENSOL", "WAAREE"],
        "mispricing_candidates": ["TATAPOWER", "ADANIENSOL"],
        "valuation_note": (
            "Regulated utilities (POWERGRID, NTPC) trade at 12-18x EV/EBITDA. "
            "Renewable energy companies at 20-30x. "
            "Solar EPC (Waaree, Sterling Wilson) at 15-25x with high growth premium."
        ),
    },
    "Information Technology": {
        "tagline": "Global tech spending recovery — BFSI + Manufacturing + AI use cases emerging",
        "cycle": "Cautious Recovery",
        "cycle_note": (
            "IT spending recovery gradual — BFSI recovering, manufacturing and retail still soft. "
            "AI/GenAI deals starting to add to TCV. Currency (USD/INR) remains a key variable. "
            "Large deals signed in FY25; execution determines FY26 revenue trajectory."
        ),
        "demand_drivers": [
            "Global IT spending recovery (BFSI, manufacturing, retail)",
            "GenAI services and AI platform implementations",
            "Cloud migration ongoing",
            "Large deal wins translating to ramp-up revenue",
        ],
        "margin_drivers": [
            "Utilisation improvement as demand recovers",
            "Attrition normalising (reduced replacement hiring costs)",
            "Offshore mix shift",
            "Automation reducing low-end headcount",
        ],
        "risks": [
            "US economic slowdown reducing tech budgets",
            "Visa restrictions affecting US delivery",
            "AI disruption reducing demand for certain service lines",
            "Currency appreciation (stronger INR)",
        ],
        "quality_cos": ["TCS", "INFY", "HCLTECH", "WIPRO"],
        "momentum_cos": ["PERSISTENT", "COFORGE", "KPITTECH"],
        "mispricing_candidates": ["TECHM", "WIPRO"],
        "valuation_note": (
            "Tier-1 IT (TCS, Infy) at 25-30x forward PE. "
            "Mid-cap IT (Persistent, Coforge) at 35-45x. "
            "Value names (Wipro, TechM) at 18-22x."
        ),
    },
    "Healthcare": {
        "tagline": "Pharma recovery underway + hospital expansion super cycle",
        "cycle": "Recovery / Upcycle",
        "cycle_note": (
            "US generics pricing stabilising. India domestic formulations growing 8-10%. "
            "Hospital sector in multi-year capacity expansion. CDMOs gaining global share."
        ),
        "demand_drivers": [
            "India domestic formulations growth — 8-10%",
            "US generics market — new product approvals",
            "CDMO contracts from global pharma companies",
            "Hospital ARPOB improvement + new bed additions",
        ],
        "margin_drivers": [
            "API cost normalisation",
            "US pricing stabilising",
            "Operating leverage in hospital segment",
            "CDMO contract mix improving",
        ],
        "risks": [
            "USFDA import alerts",
            "US generic pricing pressure",
            "Hospital capital costs (real estate, equipment)",
            "Staff costs in hospital segment",
        ],
        "quality_cos": ["SUNPHARMA", "DIVISLAB", "APOLLOHOSP"],
        "momentum_cos": ["APOLLOHOSP", "MAXHEALTH", "PERSISTENT"],
        "mispricing_candidates": ["DRREDDY", "CIPLA", "LUPIN"],
        "valuation_note": (
            "Large pharma (Sun, Divi) at 30-45x PE. "
            "Hospital chains at 40-60x EBITDA. "
            "Mid-cap pharma (Lupin, Cipla) at 20-30x — potential re-rating if US picks up."
        ),
    },
    "Financial Services": {
        "tagline": "Credit cycle intact, asset quality benign — selective opportunity",
        "cycle": "Mid Cycle",
        "cycle_note": (
            "India credit growth at 12-14% CAGR. Asset quality at decade-best levels. "
            "Interest rates in easing cycle (RBI cutting from 6.5%). "
            "NBFCs recovering after MFI stress cycle."
        ),
        "demand_drivers": [
            "India GDP growth 6.5-7% driving credit demand",
            "Housing loan growth — affordable + premium",
            "MSME and retail credit expansion",
            "Insurance penetration growth",
        ],
        "margin_drivers": [
            "NIM expansion as rate cycle turns",
            "Credit cost normalisation",
            "Operating leverage in digital banking",
        ],
        "risks": [
            "Global liquidity tightening impact",
            "MFI / microfinance stress",
            "Rising household debt levels",
            "Asset quality in unsecured retail",
        ],
        "quality_cos": ["HDFCBANK", "ICICIBANK", "KOTAKBANK"],
        "momentum_cos": ["AXISBANK", "SBIN"],
        "mispricing_candidates": ["INDUSINDBK", "BANDHANBNK"],
        "valuation_note": (
            "Top private banks at 2-3x book, 15-20x PE. "
            "PSU banks at 1-2x book. "
            "NBFCs at 25-40x PE depending on growth premium."
        ),
    },
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sec-label">Select Sector</div>', unsafe_allow_html=True)
    sectors_df = load_sectors()
    all_sectors = sorted(SECTOR_INTEL.keys())
    if not sectors_df.empty and "display_name" in sectors_df.columns:
        all_sectors = sorted(sectors_df["display_name"].dropna().tolist())

    sector = st.selectbox("Sector", all_sectors, index=0)

page_header("Sector Intelligence", sector)

# ── Get sector data ───────────────────────────────────────────────────────────
intel = SECTOR_INTEL.get(sector, {})

# Get sector row from sectors.csv
sec_row = {}
if not sectors_df.empty:
    matches = sectors_df[
        (sectors_df["sector"] == sector) | (sectors_df["display_name"] == sector)
    ]
    if not matches.empty:
        sec_row = matches.iloc[0].to_dict()

uni_df  = load_full_universe()
ob_df   = load_order_book()
news_df = load_news()

# Filter universe to this sector
if not uni_df.empty and "sector" in uni_df.columns:
    sec_companies = uni_df[uni_df["sector"] == sector]
else:
    sec_companies = pd.DataFrame()

# ── Sector hero ───────────────────────────────────────────────────────────────
tagline    = intel.get("tagline", sec_row.get("description", ""))
cycle      = intel.get("cycle", sec_row.get("cycle_position", "—"))
cycle_note = intel.get("cycle_note", "")

cycle_col = {
    "Early Upcycle": "#22c55e", "Early-to-Mid Upcycle": "#22c55e",
    "Mid Upcycle": "#3b82f6", "Late Upcycle": "#f59e0b",
    "Downcycle": "#ef4444", "Mid Cycle": "#3b82f6",
    "Recovery": "#2dd4bf", "Cautious Recovery": "#f59e0b",
    "Neutral": "#64748b",
}.get(cycle, "#64748b")

st.markdown(
    f"""<div class="sec-hero">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;">
            <div>
              <div class="sec-hero-title">{sector}</div>
              <div class="sec-hero-tag">{tagline}</div>
            </div>
            <div style="text-align:right;">
              <div style="font-size:0.62rem;text-transform:uppercase;letter-spacing:0.1em;
                color:#475569;margin-bottom:0.2rem;">Cycle Position</div>
              <div style="font-size:0.88rem;font-weight:600;color:{cycle_col};">{cycle}</div>
            </div>
          </div>
          {f'<div style="margin-top:0.75rem;font-size:0.8rem;color:#94a3b8;line-height:1.65;">{cycle_note}</div>' if cycle_note else ''}
        </div>""",
    unsafe_allow_html=True,
)

# ── KPIs from universe ────────────────────────────────────────────────────────
if not sec_companies.empty:
    mcap_total = sec_companies["market_cap_cr"].sum() if "market_cap_cr" in sec_companies.columns else 0
    n_cos      = len(sec_companies)
    ret_1d_avg = sec_companies["return_1d"].mean() * 100 if "return_1d" in sec_companies.columns else 0
    ret_1y_avg = sec_companies["return_1y"].mean() * 100 if "return_1y" in sec_companies.columns else 0

    kcols = st.columns(4)
    kpi_data = [
        ("Companies",     str(n_cos), ""),
        ("Total MCap",    fmt_cr(mcap_total), ""),
        ("Avg 1D Return", fmt_pct(ret_1d_avg), "", ret_1d_avg >= 0),
        ("Avg 1Y Return", fmt_pct(ret_1y_avg), "", ret_1y_avg >= 0),
    ]
    for col, d in zip(kcols, kpi_data):
        with col:
            kpi_card(*d[:3], delta_pos=d[3] if len(d) > 3 else None)

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tabs = st.tabs([
    "Overview", "Key Companies", "Valuation Comparison",
    "Order Book Opportunities", "Recent News",
])

# ── TAB 1: Overview ───────────────────────────────────────────────────────────
with tabs[0]:
    col1, col2 = st.columns(2)

    with col1:
        if intel.get("demand_drivers"):
            section_label("Key Demand Drivers")
            for d in intel["demand_drivers"]:
                st.markdown(
                    f'<div style="font-size:0.8rem;color:#94a3b8;padding:0.3rem 0;'
                    f'border-bottom:1px solid #111827;">• {d}</div>',
                    unsafe_allow_html=True,
                )

        if intel.get("risks"):
            st.markdown("<br>", unsafe_allow_html=True)
            section_label("Key Risks")
            for r in intel["risks"]:
                st.markdown(
                    f'<div style="font-size:0.8rem;color:#ef4444;padding:0.3rem 0;'
                    f'border-bottom:1px solid #111827;">• {r}</div>',
                    unsafe_allow_html=True,
                )

    with col2:
        if intel.get("margin_drivers"):
            section_label("Key Margin Drivers")
            for m in intel["margin_drivers"]:
                st.markdown(
                    f'<div style="font-size:0.8rem;color:#94a3b8;padding:0.3rem 0;'
                    f'border-bottom:1px solid #111827;">• {m}</div>',
                    unsafe_allow_html=True,
                )

        if intel.get("valuation_note"):
            st.markdown("<br>", unsafe_allow_html=True)
            section_label("Valuation Context")
            ai_box(intel["valuation_note"], "Valuation Note")

# ── TAB 2: Key Companies ──────────────────────────────────────────────────────
with tabs[1]:
    col1, col2, col3 = st.columns(3)
    lists = [
        ("Quality Anchor", intel.get("quality_cos", [])),
        ("Momentum Leaders", intel.get("momentum_cos", [])),
        ("Potential Mispricing", intel.get("mispricing_candidates", [])),
    ]
    for col, (title, cos) in zip([col1, col2, col3], lists):
        with col:
            section_label(title)
            for c in cos:
                mc_row = sec_companies[sec_companies["ticker"] == c] if not sec_companies.empty else pd.DataFrame()
                if not mc_row.empty:
                    r = mc_row.iloc[0]
                    ret_1d = (r.get("return_1d", 0) or 0)
                    if abs(ret_1d) < 5: ret_1d *= 100
                    cls = "pos" if ret_1d > 0 else "neg"
                    price = r.get("close") or r.get("price") or 0
                    st.markdown(
                        f"""<div style="background:#0f1929;border:1px solid #1e2d45;
                            border-radius:3px;padding:0.55rem 0.75rem;margin-bottom:0.3rem;
                            display:flex;justify-content:space-between;align-items:center;">
                            <div>
                              <div style="font-size:0.8rem;font-weight:600;color:#3b82f6;">{c}</div>
                              <div style="font-size:0.68rem;color:#475569;">{fmt_cr(r.get('market_cap_cr',''))}</div>
                            </div>
                            <div class="{cls}" style="font-size:0.78rem;font-family:'IBM Plex Mono',monospace;">
                              {fmt_pct(ret_1d)}</div>
                          </div>""",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div style="font-size:0.8rem;color:#3b82f6;padding:0.3rem 0;">{c}</div>',
                        unsafe_allow_html=True,
                    )

    st.markdown("<br>", unsafe_allow_html=True)

    if not sec_companies.empty:
        section_label("All Companies in Sector")
        DISP_COLS = ["ticker","company_name","market_cap_cr",
                     "close","return_1d","return_1y","pe","roe"]
        show_cols = [c for c in DISP_COLS if c in sec_companies.columns]
        disp = sec_companies[show_cols].copy().sort_values(
            "market_cap_cr" if "market_cap_cr" in show_cols else show_cols[0],
            ascending=False
        )
        rows = ""
        for _, r in disp.iterrows():
            ret = (r.get("return_1d", 0) or 0)
            if abs(ret) < 5: ret *= 100
            rety = (r.get("return_1y", 0) or 0)
            if abs(rety) < 5: rety *= 100
            rows += (
                f"<tr>"
                f"<td class='ticker'>{r.get('ticker','')}</td>"
                f"<td class='name'>{r.get('company_name','')}</td>"
                f"<td>{fmt_cr(r.get('market_cap_cr',''))}</td>"
                f"<td>{fmt_pct(ret)}</td>"
                f"<td>{fmt_pct(rety)}</td>"
                f"<td>{fmt_ratio(r.get('pe',''))}</td>"
                f"<td>{fmt_pct(r.get('roe',''))}</td>"
                f"</tr>"
            )
        table_wrap(
            f"""<table class='trm'>
                <thead><tr>
                  <th class='left'>Ticker</th><th class='left'>Company</th>
                  <th>MCap</th><th>1D %</th><th>1Y %</th>
                  <th>P/E</th><th>ROE</th>
                </tr></thead>
                <tbody>{rows}</tbody>
              </table>""",
        )

# ── TAB 3: Valuation Comparison ───────────────────────────────────────────────
with tabs[2]:
    section_label("Valuation Comparison — Sector Peers")
    if not sec_companies.empty and "pe" in sec_companies.columns:
        from utils.data_loader import load_fundamentals
        fund = load_fundamentals()
        if not fund.empty:
            peer_data = fund[fund["ticker"].isin(sec_companies["ticker"].tolist())]
            if not peer_data.empty:
                for metric in ["ev_ebitda", "pe", "pb", "roe"]:
                    if metric in peer_data.columns:
                        fig = peer_comparison_bar(
                            peer_data.dropna(subset=[metric]).head(15),
                            metric=metric,
                        )
                        st.plotly_chart(fig, use_container_width=True)
        else:
            info_block("Load fundamentals.csv for peer valuation comparison.")
    else:
        info_block("Fundamental data not available for this sector.")

# ── TAB 4: Order Book Opportunities ──────────────────────────────────────────
with tabs[3]:
    section_label("Order Book Opportunities")
    if ob_df.empty:
        info_block("Order book database empty.")
    else:
        sec_ob = ob_df[ob_df.get("sector", pd.Series()) == sector] if "sector" in ob_df.columns else pd.DataFrame()
        if sec_ob.empty:
            info_block(f"No order book entries for {sector}.")
        else:
            from utils.scoring import score_order_book_df
            sec_ob_s = score_order_book_df(sec_ob)
            rows = ""
            for _, r in sec_ob_s.iterrows():
                score = r.get("ob_score", 0) or 0
                from utils.formatting import score_bar, badge_html
                rows += (
                    f"<tr>"
                    f"<td class='ticker'>{r.get('ticker','')}</td>"
                    f"<td class='name'>{r.get('company_name','')}</td>"
                    f"<td>{score_bar(score, width=70)}</td>"
                    f"<td style='text-align:left;'>{badge_html(r.get('classification',''))}</td>"
                    f"<td>{fmt_cr(r.get('order_book_cr',''))}</td>"
                    f"<td>{fmt_ratio(r.get('ob_revenue_ratio',''))}</td>"
                    f"<td>{fmt_pct(r.get('revenue_growth_pct',''))}</td>"
                    f"</tr>"
                )
            table_wrap(
                f"""<table class='trm'>
                    <thead><tr>
                      <th class='left'>Ticker</th><th class='left'>Company</th>
                      <th class='left'>Score</th><th class='left'>Classification</th>
                      <th>Order Book</th><th>OB/Rev</th><th>Rev Gr</th>
                    </tr></thead>
                    <tbody>{rows}</tbody>
                  </table>""",
            )

# ── TAB 5: Recent News ────────────────────────────────────────────────────────
with tabs[4]:
    section_label("Recent News")
    if not news_df.empty and "sector" in news_df.columns:
        sec_news = news_df[news_df["sector"].astype(str).str.contains(sector.split()[0], case=False, na=False)]
        if sec_news.empty:
            info_block("No news found for this sector.")
        else:
            for _, row in sec_news.head(10).iterrows():
                s = str(row.get("sentiment", "neutral")).lower()
                col_map = {"positive": "#22c55e", "negative": "#ef4444", "neutral": "#64748b"}
                c = col_map.get(s, "#64748b")
                st.markdown(
                    f"""<div class="fil-row">
                          <div class="fil-time">{str(row.get('date',''))[:10]}</div>
                          <div class="fil-body">
                            <div class="fil-title">{row.get('headline','')}</div>
                            <div class="fil-meta">{row.get('source','')}
                              &nbsp;|&nbsp; <span style="color:{c};">{str(s).upper()}</span></div>
                            <div class="fil-ai">{row.get('ai_summary','')}</div>
                          </div>
                        </div>""",
                    unsafe_allow_html=True,
                )
    else:
        info_block("No news data loaded.")
