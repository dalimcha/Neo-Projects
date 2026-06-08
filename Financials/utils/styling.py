import streamlit as st

# ── Palette ───────────────────────────────────────────────────────────────────
BG          = "#0B1117"
BG2         = "#111827"
CARD        = "#151C26"
BORDER      = "#293241"
TEXT        = "#F8FAFC"
TEXT2       = "#9CA3AF"
TEXT3       = "#6B7280"
GOLD        = "#B08D57"
BLUE        = "#1F4E79"
GREEN       = "#059669"
AMBER       = "#D97706"
RED         = "#B91C1C"
PURPLE      = "#8B5CF6"
SLATE       = "#64748B"
SLATE2      = "#475569"

STRATEGY_COLORS = {
    "Diversified secondaries": BLUE,
    "Diversified secondaries + GP-led": "#2563EB",
    "GP-led secondaries": GOLD,
    "Single-asset CV": PURPLE,
    "Private wealth": GREEN,
    "Credit secondaries": SLATE,
    "Infrastructure": SLATE2,
    "Unknown": TEXT3,
}


def inject_css():
    st.markdown(f"""
    <style>
    /* ── Base ── */
    .stApp {{
        background-color: {BG};
        font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    }}
    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {{
        background-color: {BG2} !important;
        border-right: 1px solid {BORDER};
    }}
    section[data-testid="stSidebar"] .stRadio label {{
        font-size: 12px;
        font-weight: 600;
        color: {TEXT2};
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 6px 0;
    }}
    section[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {{
        color: {TEXT2};
        font-size: 11px;
    }}
    /* ── Headings ── */
    h1, h2, h3 {{ color: {TEXT} !important; font-weight: 700; }}
    p {{ color: {TEXT2}; }}
    /* ── Metrics ── */
    [data-testid="stMetric"] {{
        background: {CARD};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 14px 18px;
    }}
    [data-testid="stMetricLabel"] {{
        font-size: 10px !important;
        font-weight: 700 !important;
        color: {TEXT3} !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 26px !important;
        font-weight: 700 !important;
        color: {TEXT} !important;
    }}
    /* ── Dataframe ── */
    [data-testid="stDataFrame"] {{
        border: 1px solid {BORDER};
        border-radius: 4px;
    }}
    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {{
        background: {BG2};
        border-bottom: 1px solid {BORDER};
        gap: 0;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent;
        color: {TEXT3};
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        border-bottom: 2px solid transparent;
        padding: 10px 18px;
    }}
    .stTabs [aria-selected="true"] {{
        color: {GOLD} !important;
        border-bottom: 2px solid {GOLD} !important;
        background: transparent !important;
    }}
    /* ── Expander ── */
    [data-testid="stExpander"] {{
        background: {CARD};
        border: 1px solid {BORDER};
        border-radius: 4px;
    }}
    [data-testid="stExpander"] summary {{
        font-size: 12px;
        font-weight: 700;
        color: {TEXT};
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}
    /* ── Buttons ── */
    .stButton > button {{
        background: {CARD};
        color: {TEXT};
        border: 1px solid {BORDER};
        border-radius: 3px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 6px 16px;
    }}
    .stButton > button:hover {{
        border-color: {GOLD};
        color: {GOLD};
    }}
    /* ── Download button ── */
    .stDownloadButton > button {{
        background: transparent;
        color: {GOLD};
        border: 1px solid {GOLD};
        border-radius: 3px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}
    /* ── Selectbox / inputs ── */
    .stSelectbox [data-baseweb="select"] {{
        background: {CARD};
        border: 1px solid {BORDER};
    }}
    /* ── Info / warning boxes ── */
    .stAlert {{
        background: {CARD};
        border: 1px solid {BORDER};
        border-radius: 4px;
    }}
    /* ── Divider ── */
    hr {{ border-color: {BORDER}; }}
    /* ── Text areas ── */
    .stTextArea textarea {{
        background: {CARD};
        color: {TEXT};
        border: 1px solid {BORDER};
        font-family: 'Courier New', monospace;
        font-size: 12px;
    }}
    /* ── Hide streamlit chrome ── */
    #MainMenu, footer {{ visibility: hidden; }}
    </style>
    """, unsafe_allow_html=True)


# ── Render helpers ────────────────────────────────────────────────────────────

def render_kpi_card(label: str, value: str, sublabel: str = "") -> str:
    return f"""
    <div style="background:{CARD};border:1px solid {BORDER};border-radius:4px;
                padding:16px 20px;margin:4px 0;">
        <div style="font-size:10px;color:{TEXT3};text-transform:uppercase;
                    letter-spacing:0.08em;font-weight:700;margin-bottom:6px;">{label}</div>
        <div style="font-size:26px;color:{TEXT};font-weight:700;line-height:1;">{value}</div>
        {f'<div style="font-size:11px;color:{TEXT3};margin-top:6px;">{sublabel}</div>' if sublabel else ''}
    </div>"""


def render_section_header(title: str, subtitle: str = "") -> str:
    return f"""
    <div style="border-bottom:1px solid {BORDER};margin:28px 0 18px 0;padding-bottom:10px;">
        <div style="font-size:11px;font-weight:700;color:{GOLD};
                    text-transform:uppercase;letter-spacing:0.1em;">{title}</div>
        {f'<div style="font-size:12px;color:{TEXT2};margin-top:4px;">{subtitle}</div>' if subtitle else ''}
    </div>"""


def render_analyst_note(text: str) -> str:
    return f"""
    <div style="background:{CARD};border-left:3px solid {GOLD};
                padding:12px 16px;margin:16px 0;border-radius:0 4px 4px 0;">
        <div style="font-size:10px;color:{GOLD};font-weight:700;
                    text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">
            Analyst Note</div>
        <div style="font-size:12px;color:{TEXT2};line-height:1.6;">{text}</div>
    </div>"""


def render_insight_card(text: str, level: str = "neutral") -> str:
    color_map = {"neutral": BLUE, "warning": AMBER, "risk": RED, "positive": GREEN}
    color = color_map.get(level, BLUE)
    return f"""
    <div style="background:{CARD};border-left:3px solid {color};
                padding:10px 14px;margin:6px 0;border-radius:0 4px 4px 0;">
        <div style="font-size:12px;color:{TEXT2};line-height:1.5;">{text}</div>
    </div>"""


def render_warning_badge(text: str, level: str = "amber") -> str:
    colors = {"amber": AMBER, "red": RED, "green": GREEN, "blue": BLUE, "gray": TEXT3}
    bg = colors.get(level, AMBER)
    return f"""<span style="background:{bg};color:#fff;padding:2px 8px;
        border-radius:2px;font-size:10px;font-weight:700;
        letter-spacing:0.05em;white-space:nowrap;">{text}</span>"""


def render_source_confidence_badge(conf: str) -> str:
    colors = {"High": GREEN, "Medium": AMBER, "Low": RED}
    bg = colors.get(conf, TEXT3)
    return f"""<span style="background:{bg};color:#fff;padding:2px 8px;
        border-radius:2px;font-size:10px;font-weight:700;
        letter-spacing:0.05em;">{conf}</span>"""


def render_manager_card(gp_name: str, archetype: str, edge: str, risk: str,
                         neo_copy: str, neo_avoid: str, analyst_note: str,
                         fund_count: int = 0, total_aum: float = 0) -> str:
    aum_str = f"${total_aum:.1f}bn tracked across {fund_count} fund(s)" if total_aum > 0 else ""
    return f"""
    <div style="background:{CARD};border:1px solid {BORDER};border-radius:4px;
                padding:20px 24px;margin:12px 0;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;
                    margin-bottom:12px;border-bottom:1px solid {BORDER};padding-bottom:12px;">
            <div>
                <div style="font-size:15px;font-weight:700;color:{TEXT};">{gp_name}</div>
                <div style="font-size:11px;color:{GOLD};font-weight:600;
                            margin-top:3px;">{archetype}</div>
            </div>
            <div style="font-size:11px;color:{TEXT3};text-align:right;">{aum_str}</div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
            <div>
                <div style="font-size:10px;color:{TEXT3};font-weight:700;
                            text-transform:uppercase;letter-spacing:0.07em;margin-bottom:4px;">
                    Core Edge</div>
                <div style="font-size:12px;color:{TEXT2};">{edge}</div>
            </div>
            <div>
                <div style="font-size:10px;color:{RED};font-weight:700;
                            text-transform:uppercase;letter-spacing:0.07em;margin-bottom:4px;">
                    Risk to Monitor</div>
                <div style="font-size:12px;color:{TEXT2};">{risk}</div>
            </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
            <div>
                <div style="font-size:10px;color:{GREEN};font-weight:700;
                            text-transform:uppercase;letter-spacing:0.07em;margin-bottom:4px;">
                    Neo Can Copy</div>
                <div style="font-size:12px;color:{TEXT2};">{neo_copy}</div>
            </div>
            <div>
                <div style="font-size:10px;color:{AMBER};font-weight:700;
                            text-transform:uppercase;letter-spacing:0.07em;margin-bottom:4px;">
                    Neo Should Avoid</div>
                <div style="font-size:12px;color:{TEXT2};">{neo_avoid}</div>
            </div>
        </div>
        <div style="background:{BG2};border-radius:3px;padding:10px 12px;
                    border-left:2px solid {GOLD};">
            <div style="font-size:10px;color:{GOLD};font-weight:700;
                        text-transform:uppercase;letter-spacing:0.07em;margin-bottom:4px;">
                Analyst Note</div>
            <div style="font-size:12px;color:{TEXT2};font-style:italic;">{analyst_note}</div>
        </div>
    </div>"""


def render_segment_card(segment: str, definition: str, growth_driver: str,
                         return_driver: str, key_risk: str, neo_relevance: str) -> str:
    return f"""
    <div style="background:{CARD};border:1px solid {BORDER};border-radius:4px;
                padding:18px 22px;margin:10px 0;">
        <div style="font-size:13px;font-weight:700;color:{TEXT};
                    margin-bottom:10px;border-bottom:1px solid {BORDER};padding-bottom:8px;">
            {segment}</div>
        <div style="font-size:12px;color:{TEXT2};margin-bottom:10px;">{definition}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:10px;">
            <div>
                <div style="font-size:10px;color:{TEXT3};font-weight:700;
                            text-transform:uppercase;margin-bottom:3px;">Why Growing</div>
                <div style="font-size:11px;color:{TEXT2};">{growth_driver}</div>
            </div>
            <div>
                <div style="font-size:10px;color:{GREEN};font-weight:700;
                            text-transform:uppercase;margin-bottom:3px;">Return Driver</div>
                <div style="font-size:11px;color:{TEXT2};">{return_driver}</div>
            </div>
            <div>
                <div style="font-size:10px;color:{RED};font-weight:700;
                            text-transform:uppercase;margin-bottom:3px;">Key Risk</div>
                <div style="font-size:11px;color:{TEXT2};">{key_risk}</div>
            </div>
            <div>
                <div style="font-size:10px;color:{GOLD};font-weight:700;
                            text-transform:uppercase;margin-bottom:3px;">Neo Relevance</div>
                <div style="font-size:11px;color:{TEXT2};">{neo_relevance}</div>
            </div>
        </div>
    </div>"""


def render_playbook_item(title: str, body: str) -> str:
    return f"""
    <div style="background:{CARD};border:1px solid {BORDER};border-radius:4px;
                padding:14px 18px;margin:8px 0;">
        <div style="font-size:11px;font-weight:700;color:{TEXT};
                    text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">
            {title}</div>
        <div style="font-size:12px;color:{TEXT2};line-height:1.6;">{body}</div>
    </div>"""


def render_product_card(title: str, purpose: str, client_fit: str, risk: str) -> str:
    return f"""
    <div style="background:{BG2};border:1px solid {BORDER};border-left:3px solid {GOLD};
                border-radius:0 4px 4px 0;padding:16px 20px;margin:10px 0;">
        <div style="font-size:13px;font-weight:700;color:{TEXT};margin-bottom:10px;">{title}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;">
            <div>
                <div style="font-size:10px;color:{TEXT3};font-weight:700;
                            text-transform:uppercase;margin-bottom:3px;">Purpose</div>
                <div style="font-size:11px;color:{TEXT2};">{purpose}</div>
            </div>
            <div>
                <div style="font-size:10px;color:{GREEN};font-weight:700;
                            text-transform:uppercase;margin-bottom:3px;">Client Fit</div>
                <div style="font-size:11px;color:{TEXT2};">{client_fit}</div>
            </div>
            <div>
                <div style="font-size:10px;color:{RED};font-weight:700;
                            text-transform:uppercase;margin-bottom:3px;">Risk</div>
                <div style="font-size:11px;color:{TEXT2};">{risk}</div>
            </div>
        </div>
    </div>"""


def na_tag(text: str = "—") -> str:
    return f'<span style="color:{TEXT3};font-size:11px;font-style:italic;">{text}</span>'


def format_usd_bn(v) -> str:
    try:
        return f"${float(v):.1f}bn"
    except (ValueError, TypeError):
        return str(v) if str(v) not in ("nan", "None", "") else "—"


def format_pct(v) -> str:
    try:
        return f"{float(v):.1f}%"
    except (ValueError, TypeError):
        return str(v) if str(v) not in ("nan", "None", "", "NOT_AVAILABLE") else "—"


def format_multiple(v) -> str:
    try:
        return f"{float(v):.2f}x"
    except (ValueError, TypeError):
        return str(v) if str(v) not in ("nan", "None", "", "NOT_AVAILABLE") else "—"


def get_plotly_layout() -> dict:
    return dict(
        paper_bgcolor=CARD,
        plot_bgcolor=BG2,
        font=dict(color=TEXT2, family="Arial, sans-serif", size=11),
        xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, color=TEXT2),
        yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, color=TEXT2),
        legend=dict(bgcolor=CARD, bordercolor=BORDER, borderwidth=1, font=dict(size=10)),
        margin=dict(l=10, r=10, t=40, b=10),
    )
