"""
Neo Multi Family Office — Secondaries Intelligence Tracker
Streamlit dashboard
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

import database as db
from email_report import generate_report, render_text, render_html

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Neo Secondaries Intelligence Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

db.setup()

# ── Constants ─────────────────────────────────────────────────────────────────
NA_MARKERS = db.NA_MARKERS
CONFIDENCE_COLORS = {"High": "#16a34a", "Medium": "#d97706", "Low": "#dc2626"}
STATUS_COLORS = {"Closed": "#16a34a", "Fundraising": "#2563eb", "Unknown": "#6b7280"}

# ── Helpers ───────────────────────────────────────────────────────────────────
def _is_na(v):
    return str(v).strip() in NA_MARKERS or str(v).strip() in ("nan", "", "None")


def _num(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _badge(text, color):
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600">{text}</span>'


def _conf_badge(conf):
    c = CONFIDENCE_COLORS.get(conf, "#6b7280")
    return _badge(conf, c)


def _status_badge(status):
    c = STATUS_COLORS.get(status, "#6b7280")
    return _badge(status, c)


def _flag_cell(flags):
    parts = [f for f in [flags.get("irr_flag"), flags.get("dpi_flag"), flags.get("tvpi_flag")] if f]
    if not parts:
        return ""
    return " | ".join(parts)


def csv_download_button(df, filename, label="Download CSV"):
    csv = df.to_csv(index=False)
    st.download_button(label=label, data=csv, file_name=filename, mime="text/csv")


# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.image("https://img.shields.io/badge/Neo-Secondaries%20Tracker-1a3a5c?style=for-the-badge", use_container_width=True)
st.sidebar.title("Navigation")

page = st.sidebar.radio(
    "Page",
    [
        "Fund Overview",
        "Performance Monitor",
        "Strategy Map",
        "Neo Takeaways",
        "LP Commitments & Deals",
        "Sources & Alerts",
        "Weekly Update Generator",
        "Data Import",
    ],
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Filters**")

funds_df_raw = db.get_funds_df()

gp_options = sorted(funds_df_raw["gp_name"].dropna().unique().tolist())
selected_gps = st.sidebar.multiselect("GP Name", gp_options, default=[])

strategy_options = sorted(funds_df_raw["strategy_type"].dropna().unique().tolist())
selected_strategies = st.sidebar.multiselect("Strategy", strategy_options, default=[])

status_options = sorted(funds_df_raw["status"].dropna().unique().tolist())
selected_statuses = st.sidebar.multiselect("Status", status_options, default=[])

vintage_min = int(funds_df_raw["vintage_year"].min()) if len(funds_df_raw) else 2010
vintage_max = int(funds_df_raw["vintage_year"].max()) if len(funds_df_raw) else 2026
vintage_range = st.sidebar.slider("Vintage Year", vintage_min, vintage_max, (vintage_min, vintage_max))

conf_options = ["High", "Medium", "Low"]
selected_confs = st.sidebar.multiselect("Source Confidence", conf_options, default=conf_options)


def apply_filters(df):
    if selected_gps:
        df = df[df["gp_name"].isin(selected_gps)]
    if selected_strategies:
        df = df[df["strategy_type"].isin(selected_strategies)]
    if selected_statuses:
        df = df[df["status"].isin(selected_statuses)]
    if "vintage_year" in df.columns:
        df = df[df["vintage_year"].between(vintage_range[0], vintage_range[1])]
    if selected_confs and "source_confidence" in df.columns:
        df = df[df["source_confidence"].isin(selected_confs)]
    return df


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1: FUND OVERVIEW
# ─────────────────────────────────────────────────────────────────────────────
if page == "Fund Overview":
    st.title("Fund Overview")
    st.caption(
        "All tracked global private equity secondaries funds. "
        "Missing values are explicit — NOT_AVAILABLE_PUBLICLY means the data exists but is not public. "
        "NEEDS_MANUAL_REVIEW means the analyst must verify through a subscription database."
    )

    funds_df = apply_filters(funds_df_raw.copy())

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Funds Tracked", len(funds_df))
    col2.metric("Closed Funds", len(funds_df[funds_df["status"] == "Closed"]))
    col3.metric("In Market", len(funds_df[funds_df["status"] == "Fundraising"]))
    total_aum = funds_df["fund_size_usd_bn"].dropna().sum()
    col4.metric("Total AUM Tracked", f"${total_aum:.1f}bn")

    st.markdown("---")

    # Fund size bar chart
    chart_df = funds_df[funds_df["fund_size_usd_bn"].notna()].sort_values("fund_size_usd_bn", ascending=True)
    if len(chart_df):
        fig = px.bar(
            chart_df,
            x="fund_size_usd_bn",
            y="fund_name",
            color="gp_name",
            orientation="h",
            title="Fund Size by Fund (USD bn)",
            labels={"fund_size_usd_bn": "Fund Size (USD bn)", "fund_name": ""},
            height=500,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(legend_title_text="GP", margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig, use_container_width=True)

    # GP aggregate
    gp_agg = funds_df.groupby("gp_name")["fund_size_usd_bn"].sum().reset_index().sort_values("fund_size_usd_bn", ascending=False)
    fig2 = px.bar(
        gp_agg,
        x="gp_name",
        y="fund_size_usd_bn",
        title="Total Tracked AUM by GP (USD bn)",
        labels={"fund_size_usd_bn": "USD bn", "gp_name": ""},
        color="gp_name",
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    fig2.update_layout(showlegend=False, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.subheader("Fund Table")

    display_cols = [
        "fund_id", "gp_name", "fund_name", "vintage_year", "fund_size_usd_bn",
        "target_size_usd_bn", "percent_above_target", "final_close_date", "status",
        "strategy_type", "geography", "source_confidence", "notes",
    ]
    display_df = funds_df[display_cols].rename(columns={
        "fund_id": "ID", "gp_name": "GP", "fund_name": "Fund", "vintage_year": "Vintage",
        "fund_size_usd_bn": "Size ($bn)", "target_size_usd_bn": "Target ($bn)",
        "percent_above_target": "% Above Target", "final_close_date": "Close Date",
        "status": "Status", "strategy_type": "Strategy", "geography": "Geography",
        "source_confidence": "Confidence", "notes": "Notes",
    })

    st.dataframe(display_df, use_container_width=True, height=400)
    csv_download_button(funds_df, "neo_secondaries_funds.csv", "Download Funds CSV")

    st.markdown("---")
    st.subheader("Fund Detail")
    selected_fund = st.selectbox("Select fund for detail view", funds_df["fund_name"].tolist())
    if selected_fund:
        row = funds_df[funds_df["fund_name"] == selected_fund].iloc[0]
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**GP:** {row['gp_name']}")
            st.markdown(f"**Fund:** {row['fund_name']}")
            st.markdown(f"**Vintage:** {row['vintage_year']}")
            st.markdown(f"**Size:** ${row['fund_size_usd_bn']}bn")
            st.markdown(f"**Target:** {row['target_size_usd_bn']}")
            st.markdown(f"**% Above Target:** {row['percent_above_target']}")
            st.markdown(f"**Status:** {row['status']}")
            st.markdown(f"**Final Close:** {row['final_close_date']}")
        with c2:
            st.markdown(f"**Strategy:** {row['strategy_type']}")
            st.markdown(f"**Geography:** {row['geography']}")
            st.markdown(f"**LP-led Focus:** {row['lp_led_focus']}")
            st.markdown(f"**GP-led Focus:** {row['gp_led_focus']}")
            st.markdown(f"**Single Asset CV:** {row['single_asset_cv_focus']}")
            st.markdown(f"**Private Wealth:** {row['private_wealth_channel']}")
            st.markdown(f"**Source Confidence:** {row['source_confidence']}")
            if row.get("source_url") and not _is_na(row.get("source_url")):
                st.markdown(f"**Source:** [{row['source_url'][:60]}...]({row['source_url']})")
        st.markdown(f"**Notes:** {row['notes']}")
        if row.get("neo_takeaway"):
            st.info(f"**Neo Takeaway:** {row['neo_takeaway']}")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2: PERFORMANCE MONITOR
# ─────────────────────────────────────────────────────────────────────────────
elif page == "Performance Monitor":
    st.title("Performance Monitor")
    st.caption(
        "Performance data is sourced from CalSTRS LP-level capital account reports (June 30, 2025). "
        "These are **NOT** official fund-level GP returns. Do not cite as fund performance. "
        "Flags highlight analytical risks: high IRR with low DPI, NAV-heavy TVPI, young fund IRR, stale data."
    )

    st.info(
        "**LP-Reported vs Manager-Reported:** All seeded performance data is LP_REPORTED (CalSTRS). "
        "LP-reported returns reflect a single LP's capital account, which may differ from the GP's reported "
        "fund-level net IRR due to timing of capital calls, fee structures, and LP-specific arrangements."
    )

    perf_df = db.get_performance_df()
    funds_filtered = apply_filters(funds_df_raw.copy())
    perf_df = perf_df[perf_df["fund_id"].isin(funds_filtered["fund_id"])]

    # Flag summary
    col1, col2, col3 = st.columns(3)
    young_flags = perf_df[perf_df["irr_flag"].str.contains("TOO_YOUNG", na=False)]
    paper_flags = perf_df[perf_df["irr_flag"].str.contains("HIGH PAPER", na=False)]
    nav_flags = perf_df[perf_df["tvpi_flag"].str.contains("NAV-HEAVY", na=False)]
    col1.metric("Young Fund IRR Warnings", len(young_flags), help="IRR not meaningful for funds < 3 years old")
    col2.metric("High Paper IRR / Low DPI", len(paper_flags), help="High IRR but DPI < 0.3x")
    col3.metric("NAV-Heavy TVPI Warnings", len(nav_flags), help="TVPI > 1.5x but DPI < 0.5x")

    st.markdown("---")

    # Performance table
    st.subheader("Performance Data Table")
    display_cols = [
        "fund_id", "fund_name", "gp_name", "vintage_year", "as_of_date",
        "net_irr_pct", "dpi", "rvpi", "tvpi",
        "contributed_usd_m", "distributed_usd_m", "market_value_usd_m",
        "source_type", "confidence_level", "performance_scope",
        "irr_flag", "dpi_flag", "tvpi_flag", "notes",
    ]
    display_df = perf_df[[c for c in display_cols if c in perf_df.columns]]
    st.dataframe(display_df, use_container_width=True, height=400)
    csv_download_button(perf_df, "neo_performance.csv", "Download Performance CSV")

    st.markdown("---")

    # IRR vs DPI scatter
    st.subheader("IRR vs DPI Scatter")
    scatter_df = perf_df.copy()
    scatter_df["irr_num"] = scatter_df["net_irr_pct"].apply(_num)
    scatter_df["dpi_num"] = scatter_df["dpi"].apply(_num)
    scatter_df["tvpi_num"] = scatter_df["tvpi"].apply(_num)
    scatter_df["label"] = scatter_df.apply(
        lambda r: r.get("fund_name") or r["fund_id"], axis=1
    )

    irr_dpi = scatter_df.dropna(subset=["irr_num", "dpi_num"])
    if len(irr_dpi):
        fig = px.scatter(
            irr_dpi,
            x="dpi_num",
            y="irr_num",
            text="label",
            color="gp_name",
            size_max=20,
            title="Net IRR (%) vs DPI — LP-Reported (CalSTRS). High IRR + Low DPI = paper return risk.",
            labels={"dpi_num": "DPI (x)", "irr_num": "Net IRR (%)", "gp_name": "GP"},
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        # Reference lines
        fig.add_hline(y=15, line_dash="dot", line_color="gray", annotation_text="15% IRR")
        fig.add_vline(x=0.5, line_dash="dot", line_color="gray", annotation_text="0.5x DPI")
        fig.add_vline(x=1.0, line_dash="dash", line_color="green", annotation_text="1.0x DPI (capital returned)")
        fig.update_traces(textposition="top center")
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Top-left quadrant (high IRR, low DPI): paper/interim returns. Proceed with caution.")
    else:
        st.info("Insufficient numeric IRR and DPI data for scatter plot.")

    st.markdown("---")

    # TVPI vs DPI scatter
    st.subheader("TVPI vs DPI Scatter")
    tvpi_dpi = scatter_df.dropna(subset=["tvpi_num", "dpi_num"])
    if len(tvpi_dpi):
        fig2 = px.scatter(
            tvpi_dpi,
            x="dpi_num",
            y="tvpi_num",
            text="label",
            color="gp_name",
            title="TVPI vs DPI — LP-Reported (CalSTRS). High TVPI + Low DPI = NAV-heavy, realization risk.",
            labels={"dpi_num": "DPI (x)", "tvpi_num": "TVPI (x)", "gp_name": "GP"},
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig2.add_shape(type="line", x0=0, y0=0, x1=2.5, y1=2.5, line=dict(dash="dot", color="gray"))
        fig2.add_vline(x=1.0, line_dash="dash", line_color="green", annotation_text="1.0x DPI")
        fig2.update_traces(textposition="top center")
        fig2.update_layout(height=450)
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("Distance between TVPI and DPI = unrealized/NAV component. Larger gap = more realization risk.")

    st.markdown("---")

    # Flags detail
    st.subheader("Warning Flags Detail")
    flagged = perf_df[
        perf_df["irr_flag"].notna() & (perf_df["irr_flag"] != "") |
        perf_df["dpi_flag"].notna() & (perf_df["dpi_flag"] != "") |
        perf_df["tvpi_flag"].notna() & (perf_df["tvpi_flag"] != "")
    ]
    for _, row in flagged.iterrows():
        fund_label = row.get("fund_name") or row["fund_id"]
        gp = row.get("gp_name", "")
        with st.expander(f"{fund_label} ({gp}) — Flags"):
            if row.get("irr_flag"):
                st.warning(f"IRR: {row['irr_flag']}")
            if row.get("dpi_flag"):
                st.info(f"DPI: {row['dpi_flag']}")
            if row.get("tvpi_flag"):
                st.warning(f"TVPI: {row['tvpi_flag']}")
            st.markdown(f"**Net IRR:** {row['net_irr_pct']}% | **DPI:** {row['dpi']}x | **TVPI:** {row['tvpi']}x")
            st.markdown(f"**As of:** {row['as_of_date']} | **Source:** {row['source_type']} ({row['confidence_level']})")
            if row.get("notes"):
                st.markdown(f"**Notes:** {row['notes']}")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 3: STRATEGY MAP
# ─────────────────────────────────────────────────────────────────────────────
elif page == "Strategy Map":
    st.title("Strategy Map")
    st.caption(
        "Classify funds by strategy type. "
        "This helps Neo understand the competitive landscape and identify which sub-strategies are growing fastest."
    )

    funds_df = apply_filters(funds_df_raw.copy())

    STRATEGY_CATEGORIES = {
        "LP-led Diversified Secondaries": lambda r: r["lp_led_focus"] == "Yes" and r["gp_led_focus"] != "Yes",
        "Diversified (LP-led + GP-led)": lambda r: r["lp_led_focus"] == "Yes" and r["gp_led_focus"] == "Yes",
        "GP-led Specialist": lambda r: r["gp_led_focus"] == "Yes" and r["lp_led_focus"] != "Yes",
        "Single-Asset CV Specialist": lambda r: r["single_asset_cv_focus"] == "Yes",
        "Private Wealth Access": lambda r: r["private_wealth_channel"] == "Yes",
        "Co-investment / Overflow": lambda r: r["co_investment_or_overflow"] == "Yes",
    }

    def classify(row):
        cats = [cat for cat, fn in STRATEGY_CATEGORIES.items() if fn(row)]
        return cats[0] if cats else "Diversified secondaries"

    funds_df["strategy_category"] = funds_df.apply(classify, axis=1)

    # Treemap
    treemap_df = funds_df[funds_df["fund_size_usd_bn"].notna()].copy()
    if len(treemap_df):
        fig = px.treemap(
            treemap_df,
            path=["strategy_category", "gp_name", "short_name"],
            values="fund_size_usd_bn",
            color="fund_size_usd_bn",
            color_continuous_scale="Blues",
            title="Strategy Map — Fund Size Treemap (USD bn)",
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

    # Strategy breakdown table
    st.subheader("Strategy Classification Table")
    for cat in STRATEGY_CATEGORIES:
        subset = funds_df[funds_df["strategy_category"] == cat]
        if len(subset):
            st.markdown(f"#### {cat}")
            cols = ["fund_name", "gp_name", "vintage_year", "fund_size_usd_bn", "status", "geography"]
            st.dataframe(subset[cols].rename(columns={
                "fund_name": "Fund", "gp_name": "GP", "vintage_year": "Vintage",
                "fund_size_usd_bn": "Size ($bn)", "status": "Status", "geography": "Geography",
            }), use_container_width=True)

    # Strategy pie
    strat_counts = funds_df["strategy_type"].value_counts().reset_index()
    strat_counts.columns = ["Strategy", "Count"]
    fig2 = px.pie(strat_counts, names="Strategy", values="Count", title="Funds by Strategy Type")
    st.plotly_chart(fig2, use_container_width=True)

    # Feature matrix
    st.subheader("Feature Matrix")
    feature_cols = ["fund_name", "gp_name", "lp_led_focus", "gp_led_focus", "single_asset_cv_focus", "private_wealth_channel", "co_investment_or_overflow"]
    feature_df = funds_df[feature_cols].rename(columns={
        "fund_name": "Fund", "gp_name": "GP",
        "lp_led_focus": "LP-led", "gp_led_focus": "GP-led",
        "single_asset_cv_focus": "Single Asset CV",
        "private_wealth_channel": "Private Wealth",
        "co_investment_or_overflow": "Co-invest/Overflow",
    })
    st.dataframe(feature_df, use_container_width=True)
    csv_download_button(funds_df, "neo_strategy_map.csv", "Download Strategy Map CSV")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 4: NEO TAKEAWAYS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "Neo Takeaways":
    st.title("Neo Takeaways")
    st.caption(
        "For each GP, what Neo should copy, what to avoid, and relevance to Indian family-office clients. "
        "This is an internal analytical framework — update as the secondaries market evolves."
    )

    funds_df = apply_filters(funds_df_raw.copy())

    WHAT_TO_COPY = {
        "Ardian": "Data discipline, systematic LP relationship mapping, diversified secondaries underwriting process",
        "Lexington Partners": "Repeatable institutional underwriting, vintage-year diversification, private wealth channel expansion",
        "Blackstone Strategic Partners": "GP-led overlay strategy, institutional data room culture, platform integration",
        "HarbourVest Partners": "Overflow co-investment structure (separate main + overflow vehicles), primary/secondary integration",
        "Coller Capital": "Specialist secondaries identity, style discipline, LP-led + GP-led balance without drift",
        "Carlyle AlpInvest": "Hard-cap discipline + separate private wealth co-investment vehicles, institutional underwriting for private wealth",
        "Goldman Sachs Asset Management": "Structured LP education program, standardized reporting, distribution infrastructure",
        "ICG Strategic Equity": "GP-led single-asset CV underwriting checklist, GP alignment verification, strategy purity",
    }

    WHAT_TO_AVOID = {
        "Ardian": "Mega-scale strategy ($19–30bn funds require global placement Neo cannot replicate)",
        "Lexington Partners": "Over-reliance on relationship-driven deal sourcing without underwriting depth",
        "Blackstone Strategic Partners": "Conflicts between Blackstone-as-GP and Blackstone Strategic Partners-as-buyer; scale creates adverse selection at smaller deals",
        "HarbourVest Partners": "Primary fund exposure (Neo should stay secondaries-focused at early stage)",
        "Coller Capital": "Opacity on fund-level performance — Neo should be more transparent with LPs",
        "Carlyle AlpInvest": "Carlyle GP access advantage Neo cannot replicate — do not overpromise deal flow",
        "Goldman Sachs Asset Management": "Brand-only selling — IRR claims need DPI verification like any other manager",
        "ICG Strategic Equity": "Single-asset CV concentration risk — binary outcomes require deep underwriting Neo must build",
    }

    INDIA_RELEVANCE = {
        "Ardian": "Use Ardian's LP-mix transparency as benchmark for how Neo presents fund governance to HNI/UHNI LPs",
        "Lexington Partners": "Democratization through smaller commitment sizes is right model for Neo's HNI access strategy",
        "Blackstone Strategic Partners": "Private wealth push and feeder structures are template for GIFT City or SEBI AIF structures",
        "HarbourVest Partners": "Overflow structures allow smaller LP tickets into specific deals — ideal for Indian family office club deal culture",
        "Coller Capital": "Specialist positioning is easier to explain and sell to sophisticated UHNI clients than blended multi-strategy",
        "Carlyle AlpInvest": "Closest structural analog to Neo's target model — adapt their LP reporting standards",
        "Goldman Sachs Asset Management": "Education materials template for Indian HNI financial literacy in secondaries",
        "ICG Strategic Equity": "GP-led CVs underpenetrated in India — ICG framework directly applicable to Neo's Indian GP relationship network",
    }

    for gp in gp_options:
        gp_funds = funds_df[funds_df["gp_name"] == gp]
        if len(gp_funds) == 0:
            continue

        with st.expander(f"{gp} — {len(gp_funds)} fund(s) tracked", expanded=True):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown("**Funds:**")
                for _, r in gp_funds.iterrows():
                    size_str = f"${r['fund_size_usd_bn']:.1f}bn" if pd.notna(r["fund_size_usd_bn"]) else "Size TBC"
                    st.markdown(f"- {r['fund_name']} ({r['vintage_year']}) — {size_str} — {r['status']}")

            with col2:
                if gp in WHAT_TO_COPY:
                    st.markdown(f"**What Neo Should Copy:**")
                    st.success(WHAT_TO_COPY[gp])
                if gp in WHAT_TO_AVOID:
                    st.markdown(f"**What Neo Should Avoid:**")
                    st.error(WHAT_TO_AVOID[gp])
                if gp in INDIA_RELEVANCE:
                    st.markdown(f"**Relevance to Indian Family Office Clients:**")
                    st.info(INDIA_RELEVANCE[gp])

                neo_takeaway = gp_funds.iloc[0].get("neo_takeaway")
                if neo_takeaway and not _is_na(neo_takeaway):
                    st.markdown("**Full Neo Takeaway:**")
                    st.markdown(f"_{neo_takeaway}_")

    st.markdown("---")
    st.subheader("Neo Framework Summary")
    st.markdown("""
| GP | Best At | Copy | Avoid | India Relevance |
|---|---|---|---|---|
| Ardian | Data discipline | LP relationship mapping | Mega-scale | LP governance transparency |
| Lexington | Repeatable underwriting | Vintage diversification | Relationship-only sourcing | HNI access model |
| Blackstone SP | Platform integration | GP-led overlay | Conflicts, scale | GIFT City/AIF structure |
| HarbourVest | Overflow structure | Co-invest overflow vehicle | Primary exposure | Club deal structures |
| Coller | Specialist identity | Style discipline | Opacity | UHNI positioning |
| AlpInvest | Private wealth access | Hard cap + PW vehicles | GP access claims | LP reporting standards |
| Goldman | Distribution/education | Education program | Brand-only selling | HNI literacy |
| ICG | GP-led underwriting | Single-asset CV checklist | Concentration risk | Indian GP relationships |
""")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 5: LP COMMITMENTS & DEALS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "LP Commitments & Deals":
    st.title("LP Commitments & Deals")

    tab1, tab2 = st.tabs(["LP Commitments", "Deals"])

    with tab1:
        lp_df = db.get_lp_commitments_df()
        if len(lp_df) == 0:
            st.info("No LP commitment data yet. Import from PitchBook/Preqin CSV or use the Data Import page.")
            st.markdown("""
**How to populate this table:**
1. Export LP commitment data from PitchBook, Preqin, or Burgiss
2. Map columns to: `commitment_id, fund_id, lp_name, lp_type, commitment_amount_usd_m, commitment_date, source_url, confidence_level, notes`
3. Use the Data Import page or run: `python update_sources.py import --table lp_commitments --csv your_file.csv`
            """)
        else:
            st.dataframe(lp_df, use_container_width=True)
            csv_download_button(lp_df, "neo_lp_commitments.csv")

    with tab2:
        deals_df = db.get_deals_df()
        if len(deals_df) == 0:
            st.info("No deal data yet. Import from PitchBook/Preqin CSV or use the Data Import page.")
            st.markdown("""
**How to populate this table:**
1. Export secondaries deal data from PitchBook, Preqin, or Secondaries Investor
2. Map columns to: `deal_id, fund_id, deal_name, deal_type, seller_or_sponsor, underlying_company_or_fund, sector, geography, transaction_size_usd_m, entry_discount_or_premium, date_announced, date_closed, source_url, confidence_level, notes`
3. Use the Data Import page or run: `python update_sources.py import --table deals --csv your_file.csv`
            """)
        else:
            st.dataframe(deals_df, use_container_width=True)
            csv_download_button(deals_df, "neo_deals.csv")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 6: SOURCES & ALERTS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "Sources & Alerts":
    st.title("Sources & Alerts")

    tab1, tab2 = st.tabs(["Sources", "Alerts"])

    with tab1:
        st.subheader("Source Registry")
        st.caption(
            "Every data point in this tracker has a source. "
            "Subscription-required sources are flagged. "
            "Analyst should verify NEEDS_MANUAL_REVIEW items through PitchBook, Preqin, or Burgiss."
        )
        sources_df = db.get_sources_df()
        st.dataframe(sources_df, use_container_width=True, height=400)
        csv_download_button(sources_df, "neo_sources.csv")

        st.markdown("---")
        st.subheader("Subscription-Required Sources")
        sub_required = sources_df[sources_df["subscription_required"].str.upper() == "YES"]
        if len(sub_required):
            for _, row in sub_required.iterrows():
                st.warning(f"**{row['source_name']}** ({row['fund_id']}): {row['analyst_notes']}")
        else:
            st.success("No subscription-required sources flagged.")

        st.markdown("---")
        st.subheader("Sources Requiring Manual Review")
        needs_review = sources_df[sources_df["source_url"].str.contains("NEEDS_MANUAL_REVIEW", na=False)]
        if len(needs_review):
            for _, row in needs_review.iterrows():
                st.error(f"**{row['fund_id']}** — {row['analyst_notes']}")
        else:
            st.success("No NEEDS_MANUAL_REVIEW sources.")

    with tab2:
        st.subheader("Active Alerts")
        alerts_df = db.get_alerts_df()
        if len(alerts_df) == 0:
            st.info("No alerts yet. Alerts are created automatically or via: `python update_sources.py alert --fund-id F001 --type 'New close' --summary 'Close confirmed'`")
        else:
            for _, row in alerts_df.iterrows():
                importance = row.get("importance", "Medium")
                if importance == "High":
                    fn = st.error
                elif importance == "Medium":
                    fn = st.warning
                else:
                    fn = st.info
                fn(f"**[{importance}] {row.get('fund_name', row['fund_id'])}** — {row['summary']} | {row['recommended_action']}")
            csv_download_button(alerts_df, "neo_alerts.csv")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 7: WEEKLY UPDATE GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
elif page == "Weekly Update Generator":
    st.title("Weekly Update Generator")
    st.caption(
        "Generate a concise weekly email summary for Neo analysts. "
        "Covers new fund closes, performance updates, LP commitments, deals, missing data, and analyst implications."
    )

    col1, col2 = st.columns(2)
    with col1:
        since_date = st.date_input(
            "Include changes since",
            value=datetime.now() - timedelta(days=7),
        ).strftime("%Y-%m-%d")
    with col2:
        output_format = st.radio("Format", ["Plain Text", "HTML"])

    if st.button("Generate Report", type="primary"):
        with st.spinner("Generating..."):
            sections = generate_report(since_date=since_date)
            if output_format == "HTML":
                content = render_html(sections, since_date)
                st.download_button(
                    "Download HTML Report",
                    data=content,
                    file_name=f"neo_secondaries_weekly_{datetime.now().strftime('%Y%m%d')}.html",
                    mime="text/html",
                )
                st.components.v1.html(content, height=800, scrolling=True)
            else:
                content = render_text(sections, since_date)
                st.download_button(
                    "Download Text Report",
                    data=content,
                    file_name=f"neo_secondaries_weekly_{datetime.now().strftime('%Y%m%d')}.txt",
                    mime="text/plain",
                )
                st.text_area("Report Preview", content, height=600)

    st.markdown("---")
    st.subheader("Report Contents")
    st.markdown("""
The weekly report includes:

1. **New Fund Closes** — funds with `status=Closed` and `last_updated` since the cutoff date
2. **Funds in Market** — all funds with `status=Fundraising` and their current known details
3. **New Performance Data** — any performance records with `as_of_date` since the cutoff
4. **New LP Commitments** — any LP commitment records since the cutoff
5. **New Secondaries Deals** — any deal records since the cutoff
6. **Missing Data / Manual Follow-up** — funds with NOT_AVAILABLE or NEEDS_MANUAL_REVIEW fields; closed funds with no performance data
7. **Active Alerts** — all unresolved alerts
8. **Analyst Implications for Neo** — standing analytical points relevant to Neo's strategy

**Automation:** Run `python email_report.py --output report.txt` in a weekly cron job.
    """)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE 8: DATA IMPORT
# ─────────────────────────────────────────────────────────────────────────────
elif page == "Data Import":
    st.title("Data Import")
    st.caption(
        "Import data from PitchBook, Preqin, Burgiss, pension LP reports, or manually compiled CSVs. "
        "Existing records are not overwritten unless you choose append mode on duplicate primary keys. "
        "Always check source_confidence and source_type after importing."
    )

    st.subheader("Import CSV")
    table = st.selectbox("Target Table", ["funds", "performance", "deals", "lp_commitments", "alerts", "sources"])
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file:
        df_preview = pd.read_csv(uploaded_file, dtype=str)
        st.write(f"Preview: {len(df_preview)} rows, {len(df_preview.columns)} columns")
        st.dataframe(df_preview.head(5), use_container_width=True)

        if st.button("Import to Database", type="primary"):
            try:
                uploaded_file.seek(0)
                df_import = pd.read_csv(uploaded_file, dtype=str)
                conn = db.get_conn()
                df_import.to_sql(table, conn, if_exists="append", index=False)
                conn.commit()
                conn.close()
                st.success(f"Imported {len(df_import)} rows into `{table}`")
            except Exception as e:
                st.error(f"Import failed: {e}")

    st.markdown("---")
    st.subheader("Required Column Schemas")

    with st.expander("funds"):
        st.code("fund_id, gp_name, fund_name, short_name, vintage_year, fund_size_usd_bn, target_size_usd_bn, percent_above_target, final_close_year, final_close_date, status, strategy_type, geography, asset_class, lp_led_focus, gp_led_focus, single_asset_cv_focus, private_wealth_channel, co_investment_or_overflow, source_url, source_type, source_confidence, notes, last_updated")

    with st.expander("performance"):
        st.code("performance_id, fund_id, as_of_date, committed_usd_m, contributed_usd_m, distributed_usd_m, market_value_usd_m, net_irr_pct, gross_irr_pct, dpi, rvpi, tvpi, moic, pme, reported_by, source_url, source_document_name, source_type, confidence_level, performance_scope, notes")
        st.info("For unavailable values, use: NOT_AVAILABLE_PUBLICLY, SUBSCRIPTION_REQUIRED, TOO_YOUNG_TO_EVALUATE, NEEDS_MANUAL_REVIEW, STALE, MANAGER_REPORTED, or LP_REPORTED")

    with st.expander("deals"):
        st.code("deal_id, fund_id, deal_name, deal_type, seller_or_sponsor, underlying_company_or_fund, sector, geography, transaction_size_usd_m, entry_discount_or_premium, date_announced, date_closed, source_url, confidence_level, notes")

    with st.expander("lp_commitments"):
        st.code("commitment_id, fund_id, lp_name, lp_type, commitment_amount_usd_m, commitment_date, source_url, confidence_level, notes")

    st.markdown("---")
    st.subheader("PitchBook / Preqin / Burgiss Import Guide")
    st.markdown("""
1. **PitchBook**: Export fund data → map `Fund Name` → `fund_name`, `Fund Size` → `fund_size_usd_bn`, etc.
   Set `source_type = SUBSCRIPTION_REQUIRED` and `source_confidence = Medium` unless cross-verified.

2. **Preqin**: Export fund performance → map `Net IRR` → `net_irr_pct`, `DPI` → `dpi`, etc.
   Set `source_type = MANAGER_REPORTED` (Preqin collects from managers) and `confidence_level = Medium`.

3. **Burgiss**: Performance data is LP-reported. Set `source_type = LP_REPORTED`, `confidence_level = High`.
   Always fill `performance_scope` with the LP name or "Burgiss pooled LP universe".

4. **Pension LP Reports** (CalSTRS, CALPERS, etc.): Public PDF tables → parse → import.
   Set `source_type = LP_REPORTED`, `reported_by = [LP Name]`, `performance_scope = [LP] LP-level capital account`.

5. **Secondaries Investor / PEI**: News-based → `source_type = News/paywalled`, `confidence_level = Medium`.
   Always note subscription requirement in `notes`.

**Golden rule:** If you cannot verify a number with a primary source (GP press release, LP report, SEC filing),
set confidence to `Low` or `Medium` and add a `NEEDS_MANUAL_REVIEW` note.
    """)

    st.markdown("---")
    st.subheader("Download Template CSVs")
    col1, col2, col3 = st.columns(3)
    with col1:
        template_funds = pd.DataFrame(columns=[
            "fund_id", "gp_name", "fund_name", "short_name", "vintage_year",
            "fund_size_usd_bn", "target_size_usd_bn", "percent_above_target",
            "final_close_year", "final_close_date", "status", "strategy_type",
            "geography", "asset_class", "lp_led_focus", "gp_led_focus",
            "single_asset_cv_focus", "private_wealth_channel", "co_investment_or_overflow",
            "source_url", "source_type", "source_confidence", "notes", "last_updated",
        ])
        csv_download_button(template_funds, "template_funds.csv", "Fund Template CSV")
    with col2:
        template_perf = pd.DataFrame(columns=[
            "performance_id", "fund_id", "as_of_date", "committed_usd_m",
            "contributed_usd_m", "distributed_usd_m", "market_value_usd_m",
            "net_irr_pct", "gross_irr_pct", "dpi", "rvpi", "tvpi", "moic", "pme",
            "reported_by", "source_url", "source_document_name", "source_type",
            "confidence_level", "performance_scope", "notes",
        ])
        csv_download_button(template_perf, "template_performance.csv", "Performance Template CSV")
    with col3:
        template_deals = pd.DataFrame(columns=[
            "deal_id", "fund_id", "deal_name", "deal_type", "seller_or_sponsor",
            "underlying_company_or_fund", "sector", "geography",
            "transaction_size_usd_m", "entry_discount_or_premium",
            "date_announced", "date_closed", "source_url", "confidence_level", "notes",
        ])
        csv_download_button(template_deals, "template_deals.csv", "Deals Template CSV")

    st.markdown("---")
    st.subheader("Export Full Database")
    if st.button("Export All Tables to CSV"):
        for tbl_name, getter in [
            ("funds", db.get_funds_df),
            ("performance", db.get_performance_df),
            ("sources", db.get_sources_df),
        ]:
            df_export = getter()
            csv_download_button(df_export, f"neo_{tbl_name}_export.csv", f"Download {tbl_name}.csv")
