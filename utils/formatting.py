"""
formatting.py
─────────────
CSS injection, number formatters, and HTML component builders
for the India Public Markets Intelligence Terminal.
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Optional

# ── Colour palette ────────────────────────────────────────────────────────────
BG       = "#0a0e27"
BG2      = "#141b3d"
BG3      = "#1a2347"
BG4      = "#0f1533"
BORDER   = "#2d3a5f"
BORDER2  = "#3a4a76"
TEXT     = "#ffffff"
TEXT2    = "#a0aec0"
TEXT3    = "#64748b"
TEXT4    = "#4b5d82"
ACCENT   = "#00d4ff"
ACCENT2  = "#00ff88"
POS      = "#00ff88"
NEG      = "#ff3366"
WARN     = "#ffd900"
PURPLE   = "#8b7cff"
TEAL     = "#00d4ff"

# ── Global CSS ────────────────────────────────────────────────────────────────
def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap');

/* ── Reset & Base ───────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Space Mono', monospace !important;
}

/* ── Hide Streamlit chrome ─────────────────────────────────── */
#MainMenu { visibility: hidden; }
header[data-testid="stHeader"] { display: none; }
footer { display: none; }
.stDeployButton { display: none; }
[data-testid="stToolbar"] { display: none; }
[data-testid="stDecoration"] { display: none; }

/* ── App background — subtle radial depth ──────────────────── */
.stApp {
    background:
        linear-gradient(rgba(26,35,71,0.24) 1px, transparent 1px),
        linear-gradient(90deg, rgba(26,35,71,0.24) 1px, transparent 1px),
        radial-gradient(circle at 18% 10%, rgba(0,212,255,0.10) 0%, transparent 22%),
        radial-gradient(circle at 82% 0%, rgba(0,255,136,0.08) 0%, transparent 22%),
        #0a0e27 !important;
    background-size: 100px 100px, 100px 100px, auto, auto !important;
}
.main, section.main > div { background: transparent !important; }

/* ── Block container ───────────────────────────────────────── */
.main .block-container {
    padding-top: 1.5rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    padding-bottom: 3rem !important;
    max-width: 100% !important;
}

/* ── Sidebar ───────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #141b3d !important;
    border-right: 1px solid #2d3a5f !important;
    box-shadow: inset -1px 0 0 rgba(255,255,255,0.03), 10px 0 30px rgba(0,0,0,0.24) !important;
}
[data-testid="stSidebarContent"] {
    padding-top: 0 !important;
}

/* Sidebar nav links */
[data-testid="stSidebarNavLink"] {
    font-size: 0.80rem !important;
    font-weight: 600 !important;
    color: #a0aec0 !important;
    padding: 0.5rem 0.9rem !important;
    margin: 2px 8px !important;
    border-radius: 8px !important;
    transition: color 0.12s, background 0.12s, border-color 0.12s, transform 0.12s !important;
    letter-spacing: 0.01em !important;
    border: 1px solid transparent !important;
}
[data-testid="stSidebarNavLink"]:hover {
    color: #ffffff !important;
    background: #1a2347 !important;
    border-color: rgba(0,212,255,0.22) !important;
    transform: translateX(1px) !important;
}
[data-testid="stSidebarNavLink"][aria-current="page"] {
    color: #ffffff !important;
    background: linear-gradient(135deg, rgba(0,212,255,0.12), rgba(0,255,136,0.12)) !important;
    border-color: rgba(0,255,136,0.26) !important;
    font-weight: 500 !important;
    box-shadow: 0 0 0 1px rgba(0,212,255,0.12), 0 6px 16px rgba(0,0,0,0.22) !important;
}
[data-testid="stSidebarNavLink"][aria-current="page"]::before {
    content: '';
    position: absolute;
    left: 0;
    top: 20%;
    height: 60%;
    width: 2px;
    background: linear-gradient(180deg, #00d4ff, #00ff88);
    border-radius: 0 2px 2px 0;
}
[data-testid="stSidebarNavLink"] { position: relative !important; }

/* ── Typography ────────────────────────────────────────────── */
h1 {
    font-family: 'Syne', sans-serif !important;
    font-size: 3rem !important; font-weight: 800 !important;
    background: linear-gradient(135deg, #00d4ff, #00ff88);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    color: transparent !important;
    letter-spacing: -0.04em !important;
    line-height: 1.3 !important;
}
h2 {
    font-family: 'Syne', sans-serif !important;
    font-size: 0.95rem !important; font-weight: 700 !important;
    color: #ffffff !important; text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
}
h3 {
    font-family: 'Syne', sans-serif !important;
    font-size: 0.78rem !important; font-weight: 700 !important;
    color: #a0aec0 !important; text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
}
p, .stMarkdown p {
    font-size: 0.82rem !important; color: #a0aec0 !important;
    line-height: 1.68 !important;
}
code {
    font-family: 'Space Mono', monospace !important;
    font-size: 0.8em !important; color: #00d4ff !important;
    background: rgba(0,212,255,0.1) !important;
    padding: 0.1em 0.35em !important; border-radius: 3px !important;
}

/* ── Metrics ───────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #141b3d !important;
    border: 1px solid #2d3a5f !important;
    border-radius: 12px !important;
    padding: 0.9rem 1.1rem !important;
    box-shadow: 0 8px 24px rgba(0,0,0,0.20), inset 0 1px 0 rgba(255,255,255,0.03) !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
    position: relative;
    overflow: hidden;
}
[data-testid="stMetric"]:hover {
    border-color: #31527f !important;
    box-shadow: 0 12px 30px rgba(0,0,0,0.24), inset 0 1px 0 rgba(255,255,255,0.04) !important;
}
[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: linear-gradient(180deg, #00d4ff, #00ff88);
}
[data-testid="stMetricLabel"] p {
    font-family: 'Space Mono', monospace !important;
    font-size: 0.72rem !important; text-transform: uppercase !important;
    letter-spacing: 0.1em !important; color: #64748b !important;
    font-weight: 600 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'Syne', sans-serif !important;
    font-size: 2rem !important; font-weight: 700 !important;
    color: #ffffff !important; letter-spacing: -0.03em !important;
}
[data-testid="stMetricDelta"] { font-size: 0.71rem !important; }

/* ── Tabs ──────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.35rem !important;
    background: transparent !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0 !important;
    margin-bottom: 0.35rem !important;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Syne', sans-serif !important;
    font-size: 0.82rem !important; font-weight: 700 !important;
    color: #a0aec0 !important; text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
    padding: 0.7rem 1.35rem !important;
    background: #1a2347 !important;
    border: 2px solid #2d3a5f !important;
    border-radius: 8px !important;
    transition: color 0.12s, background 0.12s, border-color 0.12s !important;
}
.stTabs [data-baseweb="tab"]:hover { color: #94a3b8 !important; }
.stTabs [aria-selected="true"] {
    color: #0a0e27 !important;
    background: linear-gradient(135deg, #00d4ff, #00ff88) !important;
    border: 2px solid #00ff88 !important;
    box-shadow: 0 8px 24px rgba(0,212,255,0.22) !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.25rem !important; }

/* ── Buttons ───────────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #00d4ff, #00ff88) !important;
    border: none !important;
    color: #0a0e27 !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 0.78rem !important; font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important; border-radius: 8px !important;
    padding: 0.4rem 0.9rem !important;
    transition: all 0.15s !important;
    box-shadow: 0 8px 22px rgba(0,212,255,0.18) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 26px rgba(0,212,255,0.30) !important;
}
.stButton > button:active {
    transform: translateY(0) !important;
    box-shadow: 0 0 0 1px rgba(59,130,246,0.3) !important;
}

/* Primary button (form submit) */
.stForm [data-testid="stFormSubmitButton"] button,
[data-testid="stFormSubmitButton"] > button {
    background: rgba(37,99,235,0.15) !important;
    border-color: #2563eb !important; color: #93c5fd !important;
}
[data-testid="stFormSubmitButton"] > button:hover {
    background: rgba(37,99,235,0.25) !important;
}

/* ── Inputs / Selects ──────────────────────────────────────── */
[data-baseweb="select"] > div {
    background: #1a2347 !important;
    border-color: #2d3a5f !important;
    border-radius: 8px !important;
    min-height: 38px !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
[data-baseweb="select"] > div:hover { border-color: #2d3f5a !important; }
[data-baseweb="select"] > div:focus-within {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.15) !important;
}
[data-baseweb="select"] * { color: #ffffff !important; font-size: 0.81rem !important; }
[data-baseweb="popover"] { background: #141b3d !important; border: 1px solid #2d3a5f !important; }
[data-baseweb="menu-item"] { background: #141b3d !important; color: #a0aec0 !important; font-size: 0.81rem !important; }
[data-baseweb="menu-item"]:hover { background: #1a2347 !important; }

.stTextInput input, .stNumberInput input {
    background: linear-gradient(180deg, rgba(12,19,32,0.98) 0%, rgba(15,25,41,0.98) 100%) !important;
    border: 1px solid #1f314c !important;
    color: #cbd5e1 !important; font-size: 0.81rem !important;
    border-radius: 8px !important; transition: border-color 0.15s, box-shadow 0.15s !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.15) !important;
    outline: none !important;
}
.stTextArea textarea {
    background: linear-gradient(180deg, rgba(12,19,32,0.98) 0%, rgba(15,25,41,0.98) 100%) !important;
    border: 1px solid #1f314c !important;
    color: #cbd5e1 !important; font-size: 0.81rem !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    border-radius: 5px !important; line-height: 1.65 !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
.stTextArea textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.15) !important;
    outline: none !important;
}

/* ── Slider ────────────────────────────────────────────────── */
.stSlider [data-baseweb="slider"] [data-testid="stTickBar"] {
    color: #475569 !important;
}

/* ── Dataframe ─────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid #2d3a5f !important;
    border-radius: 12px !important; overflow: hidden !important;
    box-shadow: 0 12px 28px rgba(0,0,0,0.22) !important;
    background: #141b3d !important;
}
[data-testid="stDataFrameResizable"] {
    border-radius: 10px !important;
}
[data-testid="stDataFrame"] [role="columnheader"] {
    background: #1a2347 !important;
    color: #a0aec0 !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    border-bottom: 2px solid #2d3a5f !important;
}
[data-testid="stDataFrame"] [role="gridcell"] {
    font-size: 0.84rem !important;
    color: #ffffff !important;
    border-bottom: 1px solid #2d3a5f !important;
    font-family: 'Space Mono', monospace !important;
}
[data-testid="stDataFrame"] [data-testid="stDataFrameRow"]:hover [role="gridcell"] {
    background: #1a2347 !important;
}

/* ── Expanders ─────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #1a2840 !important; border-radius: 6px !important;
    background: #0a1020 !important; overflow: hidden !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.02) !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.79rem !important; color: #64748b !important;
    font-weight: 500 !important; padding: 0.7rem 1rem !important;
    transition: color 0.12s !important;
}
[data-testid="stExpander"] summary:hover { color: #94a3b8 !important; }

/* ── Divider / HR ──────────────────────────────────────────── */
hr { border: none !important; border-top: 1px solid #141e30 !important; margin: 0.75rem 0 !important; }

/* ── Checkbox / Radio ──────────────────────────────────────── */
.stCheckbox label p, .stRadio label p {
    font-size: 0.8rem !important; color: #94a3b8 !important;
}
.stCheckbox label span[data-testid="stMarkdownContainer"] p { margin-bottom: 0 !important; }

/* ── Alerts ────────────────────────────────────────────────── */
.stAlert { font-size: 0.8rem !important; border-radius: 6px !important; }

/* ── Progress bar ──────────────────────────────────────────── */
.stProgress [data-testid="stProgressBar"] > div {
    background: #3b82f6 !important;
}

/* ── Scrollbars ────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #1e2d45; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #2d3f5a; }

/* ── Spinner ───────────────────────────────────────────────── */
.stSpinner > div { border-top-color: #3b82f6 !important; }

/* ═══════════════════════════════════════════════════════════════
   CUSTOM COMPONENTS
   ═══════════════════════════════════════════════════════════════ */

/* ── Page header ───────────────────────────────────────────── */
.pg-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0.1rem 0 1rem 0;
    border-bottom: 1px solid #162338;
    margin-bottom: 1.3rem;
    position: relative;
}
.pg-header::after {
    content: '';
    position: absolute;
    bottom: -1px; left: 0;
    width: 48px; height: 2px;
    background: linear-gradient(90deg, #3b82f6, transparent);
    border-radius: 2px;
}
.pg-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.4rem; font-weight: 800;
    background: linear-gradient(135deg, #00d4ff, #00ff88);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    color: transparent;
    letter-spacing: -0.04em;
}
.pg-subtitle {
    font-size: 0.76rem; color: #6f8aac; margin-left: 0.85rem;
}
.pg-ts {
    font-family: 'JetBrains Mono', monospace; font-size: 0.67rem;
    color: #2d3f5a; letter-spacing: 0.02em;
}

/* ── Section labels ────────────────────────────────────────── */
.sec-label {
    display: flex; align-items: center; gap: 8px;
    font-size: 0.61rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.11em; color: #3d5270;
    margin-bottom: 0.65rem; padding-bottom: 0.35rem;
    border-bottom: 1px solid #0f1929;
}
.sec-label::before {
    content: '';
    display: inline-block;
    width: 3px; height: 11px;
    background: linear-gradient(180deg, #3b82f6, #1d4ed8);
    border-radius: 2px; flex-shrink: 0;
}

/* ── KPI card ──────────────────────────────────────────────── */
.kpi {
    background: #141b3d;
    border: 1px solid #2d3a5f;
    border-radius: 12px;
    padding: 0.9rem 1.1rem 0.85rem;
    box-shadow: 0 8px 22px rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.025);
    transition: border-color 0.15s, box-shadow 0.15s;
    position: relative; overflow: hidden;
}
.kpi:hover {
    border-color: #2a3d5a;
    box-shadow: 0 4px 14px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.04);
}
.kpi-lbl {
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.11em;
    color: #64748b; font-weight: 700; margin-bottom: 0.4rem;
}
.kpi-val {
    font-family: 'Syne', sans-serif;
    font-size: 1.8rem; font-weight: 700; color: #ffffff;
    letter-spacing: -0.025em; line-height: 1.1;
}
.kpi-sub {
    font-family: 'Space Mono', monospace;
    font-size: 0.71rem; margin-top: 0.2rem;
}

/* ── Index ticker bar ──────────────────────────────────────── */
.idx-bar {
    background: #141b3d;
    border: 1px solid #2d3a5f;
    border-radius: 12px;
    padding: 0.9rem 1.1rem;
    display: flex; flex-direction: column; gap: 0.2rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.025);
    transition: border-color 0.15s, box-shadow 0.15s;
    position: relative; overflow: hidden;
}
.idx-bar:hover {
    border-color: #2a3d5a;
    box-shadow: 0 4px 14px rgba(0,0,0,0.5);
}
.idx-bar.idx-up { border-bottom: 2px solid #166534; }
.idx-bar.idx-dn { border-bottom: 2px solid #7f1d1d; }
.idx-name {
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.11em;
    color: #64748b; font-weight: 700;
}
.idx-val {
    font-family: 'Syne', sans-serif;
    font-size: 1.65rem; font-weight: 700; color: #ffffff;
    letter-spacing: -0.03em; line-height: 1.15;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.idx-chg {
    font-family: 'JetBrains Mono', monospace; font-size: 0.77rem; font-weight: 600;
}

/* ── Table wrapper ─────────────────────────────────────────── */
.tbl-wrap {
    background: #141b3d;
    border: 1px solid #2d3a5f;
    border-radius: 12px; overflow: hidden;
    margin-bottom: 1rem;
    box-shadow: 0 12px 30px rgba(0,0,0,0.20);
}
.tbl-cap {
    padding: 0.62rem 0.95rem; border-bottom: 1px solid #162338;
    font-size: 0.61rem; text-transform: uppercase; letter-spacing: 0.1em;
    color: #a0aec0; font-weight: 700;
    background: #1a2347;
    display: flex; justify-content: space-between; align-items: center;
}
table.trm {
    width: 100%; border-collapse: collapse;
    font-size: 0.84rem; font-family: 'Space Mono', monospace;
}
table.trm th {
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.09em;
    color: #a0aec0; font-weight: 700; padding: 0.75rem 0.95rem;
    border-bottom: 2px solid #2d3a5f; white-space: nowrap;
    text-align: right; background: #1a2347;
    font-family: 'Syne', sans-serif;
    position: sticky; top: 0; z-index: 1;
}
table.trm th.left { text-align: left; }
table.trm td {
    padding: 0.9rem 0.95rem; border-bottom: 1px solid #2d3a5f;
    color: #ffffff; white-space: nowrap; text-align: right;
    transition: background 0.08s, color 0.08s;
}
table.trm td.left {
    text-align: left; font-family: 'Space Mono', monospace; color: #ffffff;
}
table.trm td.ticker {
    color: #00d4ff; font-weight: 700; text-align: left;
    letter-spacing: 0.02em;
    font-family: 'Syne', sans-serif;
    text-transform: uppercase;
    font-size: 1rem;
}
table.trm td.name {
    color: #a0aec0; text-align: left; font-size: 0.88rem;
    font-family: 'Space Mono', monospace;
    max-width: 180px; overflow: hidden; text-overflow: ellipsis;
}
table.trm tr:hover td { background: #1a2347 !important; color: #ffffff !important; }
table.trm tr:hover td.ticker { color: #00d4ff; }
table.trm tr:last-child td { border-bottom: none; }

/* ── Colour helpers ────────────────────────────────────────── */
.pos { color: #22c55e !important; }
.neg { color: #ef4444 !important; }
.neu { color: #475569 !important; }
.hi  { color: #e2e8f0 !important; }
.acc { color: #3b82f6 !important; }
.wrn { color: #f59e0b !important; }
.pur { color: #a78bfa !important; }

/* ── Classification badges ─────────────────────────────────── */
.badge {
    display: inline-flex; align-items: center;
    padding: 0.25rem 0.75rem; border-radius: 12px;
    font-size: 0.75rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.06em;
    white-space: nowrap;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
}
.bdg-hc  { background: #052e16; color: #4ade80; border: 1px solid #166534; }
.bdg-wl  { background: #0c1f3d; color: #60a5fa; border: 1px solid #1e40af; }
.bdg-res { background: #2d1a00; color: #fb923c; border: 1px solid #92400e; }
.bdg-mbe { background: #2e1065; color: #c084fc; border: 1px solid #6b21a8; }
.bdg-vt  { background: #1c1917; color: #78716c; border: 1px solid #44403c; }
.bdg-av  { background: #450a0a; color: #f87171; border: 1px solid #991b1b; }
.bdg-pos { background: rgba(0,255,136,0.15); color: #00ff88; border: 1px solid #00ff88; }
.bdg-neg { background: rgba(255,51,102,0.15); color: #ff3366; border: 1px solid #ff3366; }
.bdg-neu { background: #1c1917; color: #78716c; border: 1px solid #44403c; }

/* ── Idea card ─────────────────────────────────────────────── */
.idea-card {
    background: linear-gradient(180deg, rgba(16,26,43,0.98) 0%, rgba(12,22,34,0.98) 100%);
    border: 1px solid #1d304c;
    border-left: 3px solid #2563eb;
    border-radius: 0 10px 10px 0;
    padding: 1rem 1.2rem; margin-bottom: 0.75rem;
    box-shadow: 0 10px 26px rgba(0,0,0,0.18);
    transition: border-color 0.15s, box-shadow 0.15s;
}
.idea-card:hover {
    border-top-color: #2a3d5a; border-right-color: #2a3d5a;
    border-bottom-color: #2a3d5a;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
}
.idea-card.hc { border-left-color: #16a34a; }
.idea-card.hc:hover { box-shadow: 0 4px 12px rgba(34,197,94,0.06); }
.idea-card.wl { border-left-color: #2563eb; }
.idea-card.res { border-left-color: #d97706; }
.idea-title { font-size: 0.88rem; font-weight: 600; color: #e2e8f0; margin-bottom: 0.3rem; }
.idea-meta {
    font-size: 0.69rem; color: #3d5270;
    margin-bottom: 0.5rem; font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.02em;
}
.idea-body { font-size: 0.79rem; color: #64748b; line-height: 1.65; }
.idea-grid { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.5rem; }
.idea-tag {
    background: rgba(17,24,39,0.8); border: 1px solid #1e2d45;
    padding: 0.18rem 0.5rem; border-radius: 4px; font-size: 0.63rem;
    color: #475569; font-family: 'JetBrains Mono', monospace;
}

/* ── Filing row ────────────────────────────────────────────── */
.fil-row {
    display: flex; padding: 0.8rem 0.75rem 0.8rem 0.95rem;
    border-bottom: 1px solid #111e30; gap: 0.95rem;
    align-items: flex-start;
    border-left: 2px solid transparent;
    transition: border-left-color 0.12s, background 0.1s;
}
.fil-row:hover {
    background: rgba(15,25,41,0.72);
    border-left-color: #2563eb;
}
.fil-row:last-child { border-bottom: none; }
.fil-time {
    font-family: 'JetBrains Mono', monospace; font-size: 0.67rem;
    color: #3d5270; white-space: nowrap; min-width: 4.5rem; padding-top: 0.1rem;
}
.fil-body { flex: 1; }
.fil-title {
    font-size: 0.8rem; font-weight: 500; color: #d9e5f3;
    line-height: 1.45; margin-bottom: 0.2rem;
}
.fil-meta {
    font-size: 0.67rem; color: #3d5270; font-family: 'JetBrains Mono', monospace;
}
.fil-ai {
    font-size: 0.73rem; color: #8fa6c2; margin-top: 0.42rem;
    padding: 0.45rem 0.75rem;
    background: rgba(7,17,32,0.82);
    border-radius: 8px; border-left: 2px solid #1e3a5f; line-height: 1.6;
}

/* ── AI summary box ────────────────────────────────────────── */
.ai-box {
    background: linear-gradient(180deg, #0d1f38 0%, #0a1928 100%);
    border: 1px solid #1e3a5f; border-radius: 6px;
    padding: 1rem 1.2rem; margin-bottom: 1rem;
    box-shadow: 0 0 24px rgba(59,130,246,0.05), 0 2px 8px rgba(0,0,0,0.4);
    position: relative; overflow: hidden;
}
.ai-box::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(59,130,246,0.4), transparent);
}
.ai-lbl {
    font-size: 0.59rem; text-transform: uppercase; letter-spacing: 0.12em;
    color: #3b82f6; font-weight: 700; margin-bottom: 0.5rem;
    display: flex; align-items: center; gap: 6px;
}
.ai-lbl::before {
    content: '';
    display: inline-block; width: 6px; height: 6px;
    background: #3b82f6; border-radius: 50%;
    box-shadow: 0 0 6px #3b82f6;
}
.ai-txt { font-size: 0.81rem; color: #94a3b8; line-height: 1.75; }

/* ── Info / warn / ok blocks ───────────────────────────────── */
.info-blk {
    background: rgba(12,30,51,0.6); border: 1px solid #1e3a5f;
    border-left: 3px solid #2563eb; border-radius: 4px;
    padding: 0.7rem 1rem; font-size: 0.79rem; color: #64748b;
    line-height: 1.65; margin-bottom: 0.75rem;
}
.warn-blk {
    background: rgba(28,17,0,0.7); border: 1px solid #92400e;
    border-left: 3px solid #d97706; border-radius: 4px;
    padding: 0.7rem 1rem; font-size: 0.79rem; color: #d97706;
    line-height: 1.65; margin-bottom: 0.75rem;
}
.ok-blk {
    background: rgba(5,46,22,0.6); border: 1px solid #166534;
    border-left: 3px solid #16a34a; border-radius: 4px;
    padding: 0.7rem 1rem; font-size: 0.79rem; color: #4ade80;
    line-height: 1.65; margin-bottom: 0.75rem;
}

/* ── Sector hero ───────────────────────────────────────────── */
.sec-hero {
    background: linear-gradient(180deg, #0f1929 0%, #0c1622 100%);
    border: 1px solid #1a2840; border-radius: 6px;
    padding: 1.2rem 1.5rem; margin-bottom: 1rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.4);
}
.sec-hero-title {
    font-size: 1rem; font-weight: 600; color: #e2e8f0;
    margin-bottom: 0.3rem; letter-spacing: -0.01em;
}
.sec-hero-tag { font-size: 0.78rem; color: #3d5270; }

/* ── Score bar ─────────────────────────────────────────────── */
.score-bar-wrap {
    height: 8px; background: #0a1020; border-radius: 4px;
    overflow: hidden; margin-top: 0.25rem;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.5);
}
.score-bar-fill {
    height: 100%; border-radius: 4px;
    position: relative; overflow: hidden;
}
.score-bar-fill::after {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; bottom: 0;
    background: linear-gradient(90deg, transparent 60%, rgba(255,255,255,0.08) 100%);
    border-radius: 4px;
}

/* ── Live status dot ───────────────────────────────────────── */
.status-dot {
    display: inline-flex; align-items: center; gap: 5px;
    font-size: 0.62rem; color: #3d5270;
    font-family: 'IBM Plex Mono', monospace;
}
.status-dot::before {
    content: '';
    display: inline-block; width: 5px; height: 5px;
    border-radius: 50%; background: #22c55e;
    box-shadow: 0 0 5px rgba(34,197,94,0.6);
    animation: pulse-dot 2.5s ease-in-out infinite;
}
@keyframes pulse-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* ── Terminal header bar (home page) ───────────────────────── */
.term-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 0 1.5rem 0; margin-bottom: 0.5rem;
}
.term-title {
    font-family: 'Space Grotesk', 'Inter', sans-serif;
    font-size: 1.4rem; font-weight: 700; color: #f8fbff;
    letter-spacing: -0.025em; line-height: 1.2;
}
.term-tagline {
    font-size: 0.75rem; color: #3d5270; margin-top: 0.3rem; letter-spacing: 0.01em;
}

/* ── Module grid cards ─────────────────────────────────────── */
.mod-card {
    background: linear-gradient(180deg, #0f1929 0%, #0c1622 100%);
    border: 1px solid #1a2840; border-radius: 7px;
    padding: 1.15rem 1.3rem; margin-bottom: 0.8rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.02);
    transition: border-color 0.18s, box-shadow 0.18s, transform 0.18s;
    cursor: default;
}
.mod-card:hover {
    border-color: #2a3d5a;
    box-shadow: 0 6px 18px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.03);
    transform: translateY(-1px);
}
.mod-card.primary {
    border-color: #1e3a6b;
    background: linear-gradient(180deg, #0e1d35 0%, #0a1628 100%);
    box-shadow: 0 1px 4px rgba(0,0,0,0.5), 0 0 24px rgba(37,99,235,0.06), inset 0 1px 0 rgba(59,130,246,0.06);
}
.mod-card.primary:hover {
    border-color: #2563eb;
    box-shadow: 0 6px 20px rgba(0,0,0,0.55), 0 0 32px rgba(37,99,235,0.1), inset 0 1px 0 rgba(59,130,246,0.08);
}
.mod-num {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.63rem; font-weight: 600; color: #1e3a5f;
    letter-spacing: 0.08em; margin-bottom: 0.45rem;
    display: flex; align-items: center; gap: 8px;
}
.mod-num.primary { color: #2563eb; }
.mod-name { font-size: 0.91rem; font-weight: 600; color: #cbd5e1; margin-bottom: 0.35rem; letter-spacing: -0.01em; }
.mod-name { font-family: 'Space Grotesk', 'Inter', sans-serif; }
.mod-name.primary { color: #93c5fd; }
.mod-desc { font-size: 0.77rem; color: #3d5270; line-height: 1.65; margin-bottom: 0.65rem; }
.mod-tags { display: flex; flex-wrap: wrap; gap: 0.3rem; }
.mod-tag {
    background: rgba(10,16,32,0.8); border: 1px solid #141e30;
    padding: 0.15rem 0.5rem; border-radius: 4px;
    font-size: 0.59rem; font-weight: 600; color: #2d3f5a;
    letter-spacing: 0.04em; text-transform: uppercase;
    font-family: 'IBM Plex Sans', sans-serif;
}
.mod-card.primary .mod-tag {
    background: rgba(30,58,107,0.4); border-color: #1e3a6b; color: #2563eb;
}

/* ── Data status bar ───────────────────────────────────────── */
.data-bar {
    display: flex; align-items: center; gap: 1.5rem;
    padding: 0.7rem 1rem; margin-top: 1rem;
    background: linear-gradient(180deg, rgba(9,17,32,0.98) 0%, rgba(7,16,30,0.98) 100%);
    border: 1px solid #14243b;
    border-radius: 10px; font-size: 0.69rem;
    font-family: 'JetBrains Mono', monospace; color: #2d3f5a;
    box-shadow: 0 10px 24px rgba(0,0,0,0.18);
}
.data-bar-item { display: flex; align-items: center; gap: 5px; }
.data-bar-item span.val { color: #475569; }
.data-bar-sep { color: #141e30; }

/* ── Utility surfaces ─────────────────────────────────────── */
.surface {
    background: #141b3d;
    border: 1px solid #2d3a5f;
    border-radius: 12px;
    padding: 1rem 1.15rem;
    box-shadow: 0 12px 28px rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.025);
    margin-bottom: 0.95rem;
}
.surface-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.11em;
    color: #a0aec0;
    font-weight: 700;
    margin-bottom: 0.55rem;
}
.surface-note {
    font-size: 0.84rem;
    color: #a0aec0;
    line-height: 1.65;
}
.mini-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.75rem;
}
.mini-stat {
    padding: 0.8rem 0.9rem;
    border-radius: 10px;
    border: 1px solid #2d3a5f;
    background: #1a2347;
}
.mini-stat-k {
    font-size: 0.64rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    margin-bottom: 0.35rem;
}
.mini-stat-v {
    font-family: 'Syne', sans-serif;
    font-size: 1.25rem;
    color: #ffffff;
    font-weight: 700;
}
.mini-stat-s {
    font-size: 0.72rem;
    color: #a0aec0;
    margin-top: 0.18rem;
}
.pill-nav {
    display:flex;
    flex-wrap:wrap;
    gap:0.6rem;
    margin:0.2rem 0 1rem 0;
}
.pill-chip {
    display:inline-flex;
    align-items:center;
    gap:0.4rem;
    padding:0.55rem 0.85rem;
    border-radius:999px;
    border:2px solid #2d3a5f;
    background:#1a2347;
    color:#a0aec0;
    font-size:0.70rem;
    font-weight:600;
    letter-spacing:0.02em;
    box-shadow:0 8px 20px rgba(0,0,0,0.14);
}
.pill-chip strong {
    color:#ffffff;
    font-family:'Syne', sans-serif;
    font-size:0.82rem;
}
.ticker-glow {
    font-family:'Syne', sans-serif;
    font-weight:700;
    letter-spacing:0.03em;
    color:#00d4ff;
    text-transform:uppercase;
    text-shadow:0 0 18px rgba(103,216,255,0.16);
}
.hero-panel {
    background:
      linear-gradient(135deg, rgba(20,27,61,0.98) 0%, rgba(16,22,52,0.98) 68%),
      radial-gradient(circle at top right, rgba(0,255,136,0.08) 0%, transparent 28%);
    border:1px solid #2d3a5f;
    border-radius:16px;
    padding:1.15rem 1.2rem;
    box-shadow:0 18px 40px rgba(0,0,0,0.22), inset 0 1px 0 rgba(255,255,255,0.03);
    margin-bottom:1rem;
    position:relative;
    overflow:hidden;
}
.hero-panel::before {
    content:'';
    position:absolute;
    inset:0 auto auto 0;
    width:100%;
    height:1px;
    background:linear-gradient(90deg, rgba(0,212,255,0), rgba(0,212,255,0.65), rgba(0,255,136,0.55), rgba(0,212,255,0));
}
.hero-title {
    font-family:'Syne', sans-serif;
    font-size:2.1rem;
    font-weight:800;
    background: linear-gradient(135deg, #00d4ff, #00ff88);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    color: transparent;
    letter-spacing:-0.04em;
    margin-bottom:0.28rem;
}
.hero-sub {
    color:#a0aec0;
    font-size:0.96rem;
    line-height:1.65;
}
</style>
"""


# ── Number formatters ─────────────────────────────────────────────────────────

def fmt_cr(val, decimals: int = 0, na: str = "—") -> str:
    """Format value in crores: 1,23,456 Cr"""
    try:
        v = float(val)
        if v >= 1_00_000:
            return f"{v/1_00_000:,.1f}L Cr"
        return f"{v:,.{decimals}f} Cr"
    except (TypeError, ValueError):
        return na


def fmt_lakh_cr(val, na: str = "—") -> str:
    try:
        v = float(val)
        return f"₹{v/1_00_000:.2f}L Cr"
    except (TypeError, ValueError):
        return na


def fmt_pct(val, decimals: int = 1, na: str = "—", sign: bool = True) -> str:
    try:
        v = float(val)
        s = "+" if (sign and v > 0) else ""
        return f"{s}{v:.{decimals}f}%"
    except (TypeError, ValueError):
        return na


def fmt_price(val, na: str = "—") -> str:
    try:
        v = float(val)
        if v >= 10_000:
            return f"₹{v:,.0f}"
        return f"₹{v:,.2f}"
    except (TypeError, ValueError):
        return na


def fmt_ratio(val, decimals: int = 1, na: str = "—") -> str:
    try:
        v = float(val)
        return f"{v:.{decimals}f}x"
    except (TypeError, ValueError):
        return na


def fmt_vol(val, na: str = "—") -> str:
    try:
        v = float(val)
        if v >= 1e7:
            return f"{v/1e7:.1f}Cr"
        if v >= 1e5:
            return f"{v/1e5:.1f}L"
        return f"{v:,.0f}"
    except (TypeError, ValueError):
        return na


def fmt_mcap(val, na: str = "—") -> str:
    try:
        v = float(val)
        if v >= 1_00_000:
            return f"₹{v/1_00_000:.1f}L Cr"
        if v >= 1_000:
            return f"₹{v:,.0f} Cr"
        return f"₹{v:.0f} Cr"
    except (TypeError, ValueError):
        return na


# ── Colour helpers ────────────────────────────────────────────────────────────

def pct_color(val: float) -> str:
    try:
        v = float(val)
        if v > 0:   return "pos"
        if v < 0:   return "neg"
        return "neu"
    except (TypeError, ValueError):
        return "neu"


def html_pct(val, decimals: int = 1) -> str:
    txt = fmt_pct(val, decimals)
    cls = pct_color(val)
    return f'<span class="{cls}">{txt}</span>'


def score_color(score: float) -> str:
    if score >= 70: return "#22c55e"
    if score >= 50: return "#3b82f6"
    if score >= 35: return "#f59e0b"
    return "#ef4444"


def score_glow(score: float) -> str:
    """Return rgba glow color for score bar shadow"""
    if score >= 70: return "rgba(34,197,94,0.35)"
    if score >= 50: return "rgba(59,130,246,0.35)"
    if score >= 35: return "rgba(245,158,11,0.35)"
    return "rgba(239,68,68,0.35)"


# ── Classification helpers ────────────────────────────────────────────────────

CLASSIFICATION_BADGE = {
    "High Conviction Idea": ("bdg-hc",  "HIGH CONVICTION"),
    "Watchlist Add":        ("bdg-wl",  "WATCHLIST"),
    "Needs More Research":  ("bdg-res", "RESEARCH"),
    "Momentum But Expensive":("bdg-mbe","MOMENTUM / RICH"),
    "Value Trap":           ("bdg-vt",  "VALUE TRAP"),
    "Avoid":                ("bdg-av",  "AVOID"),
}

def badge_html(classification: str) -> str:
    css, label = CLASSIFICATION_BADGE.get(
        classification, ("bdg-neu", classification.upper())
    )
    return f'<span class="badge {css}">{label}</span>'


SENTIMENT_BADGE = {
    "positive": "bdg-pos",
    "negative": "bdg-neg",
    "neutral":  "bdg-neu",
}

def sentiment_badge(sentiment: str) -> str:
    css = SENTIMENT_BADGE.get(sentiment.lower(), "bdg-neu")
    return f'<span class="badge {css}">{sentiment.upper()}</span>'


# ── Streamlit component wrappers ──────────────────────────────────────────────

def page_header(
    title: str,
    subtitle: str = "",
    ts: bool = True,
    data_status: str | None = None,
    data_ts: str | None = None,
) -> None:
    """
    Render the page header.

    `data_status` may be "Fresh" | "Delayed" | "Stale" | "Failed" | None.
    When None (default), no status dot is shown — never lie about freshness.
    `data_ts` is the data-as-of timestamp (distinct from page render time).
    """
    now_str = datetime.now().strftime("%d %b %Y  %H:%M") if ts else ""
    title_safe = title
    sub_html = f'<span class="hero-sub" style="margin:0;">{subtitle}</span>' if subtitle else ""

    dot_html = ""
    if data_status:
        colour = {
            "Fresh":   "#22c55e",
            "Delayed": "#f59e0b",
            "Stale":   "#ef4444",
            "Failed":  "#ef4444",
        }.get(data_status, "#64748b")
        dot_html = (
            f'<span class="pill-chip" style="border-color:{colour}55;color:{colour};'
            f'background:rgba(9,15,28,0.88);">'
            f'<span style="width:7px;height:7px;border-radius:50%;background:{colour};'
            f'box-shadow:0 0 10px {colour}aa;display:inline-block;"></span>'
            f'Data {data_status}</span>'
        )

    data_ts_html = (
        f'<span class="pill-chip"><strong>Data</strong>{data_ts}</span>'
        if data_ts else ""
    )
    page_ts_html = (
        f'<span class="pill-chip"><strong>Rendered</strong>{now_str}</span>'
    )

    left, right = st.columns([1.7, 1.0])
    with left:
        st.markdown(
            f"""<div class="hero-panel" style="padding:1.15rem 1.2rem 0.95rem;">
                  <div style="display:flex;align-items:flex-end;gap:0.55rem;flex-wrap:wrap;">
                    <span style="
                        font-family:'Syne',sans-serif;
                        font-size:clamp(2.1rem, 3.7vw, 3.8rem);
                        font-weight:800;
                        line-height:0.98;
                        letter-spacing:-0.055em;
                        text-transform:none;
                        background:linear-gradient(135deg,#00d4ff 0%,#6be8ff 30%,#00ff88 100%);
                        -webkit-background-clip:text;
                        -webkit-text-fill-color:transparent;
                        background-clip:text;
                        color:transparent;
                        display:inline-block;
                        text-shadow:0 0 30px rgba(0,212,255,0.12);
                    ">{title_safe}</span>
                    {sub_html}
                  </div>
                  <div style="display:flex;gap:0.55rem;flex-wrap:wrap;margin-top:0.9rem;">
                    <span class="pill-chip"><strong>Terminal</strong>India Public Markets</span>
                    <span class="pill-chip"><strong>Mode</strong>Research</span>
                    <span class="pill-chip"><strong>Surface</strong>{title_safe}</span>
                  </div>
                </div>""",
            unsafe_allow_html=True,
        )
    with right:
        right_html = "".join([x for x in [dot_html, data_ts_html, page_ts_html] if x])
        st.markdown(
            f"""<div class="hero-panel" style="padding:1rem 1rem 0.95rem;text-align:right;min-height:100%;">
                  <div class="hero-sub" style="margin:0 0 0.5rem 0;">Operational Status</div>
                  {right_html}
                </div>""",
            unsafe_allow_html=True,
        )


def section_label(text: str) -> None:
    st.markdown(f'<div class="sec-label">{text}</div>', unsafe_allow_html=True)


def kpi_card(label: str, value: str, delta: str = "", delta_pos: bool | None = None) -> None:
    if delta:
        cls = "pos" if delta_pos else ("neg" if delta_pos is False else "neu")
        delta_html = f'<div class="kpi-sub {cls}">{delta}</div>'
    else:
        delta_html = ""
    st.markdown(
        f"""<div class="kpi">
              <div class="kpi-lbl">{label}</div>
              <div class="kpi-val">{value}</div>
              {delta_html}
            </div>""",
        unsafe_allow_html=True,
    )


def index_card(
    name: str, value: str, change: str, pts: str,
    is_up: bool | None,
    source: str = "",
    data_ts: str = "",
) -> None:
    """
    Index ticker card.

    Renders 'N/A' cleanly when value is missing. Never shows fake change %%
    when value is missing.
    """
    missing = (value in ("", "—", None) or value == "N/A")

    cls     = "pos" if is_up else ("neg" if is_up is False else "neu")
    dir_cls = "idx-up" if is_up else ("idx-dn" if is_up is False else "")

    if missing:
        val_html = ('<div class="idx-val" style="color:#3d5270;font-size:1rem;">'
                    'N/A</div>')
        chg_html = ('<div class="idx-chg neu" style="color:#3d5270;">'
                    'Data not available</div>')
        dir_cls = ""
    else:
        val_html = f'<div class="idx-val">{value}</div>'
        chg_html = (
            f'<div class="idx-chg {cls}">'
            f'<span>{change}</span>'
            f'&nbsp;<span style="color:#3d5270;">{pts}</span>'
            f'</div>'
        )

    src_html = ""
    if source or data_ts:
        src_html = (
            f'<div style="font-size:0.58rem;color:#2d3f5a;margin-top:0.3rem;'
            f'font-family:\'IBM Plex Mono\',monospace;letter-spacing:0.02em;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
            f'{source}{" · " if source and data_ts else ""}{data_ts}'
            f'</div>'
        )

    st.markdown(
        f"""<div class="idx-bar {dir_cls}">
              <div class="idx-name">{name}</div>
              {val_html}
              {chg_html}
              {src_html}
            </div>""",
        unsafe_allow_html=True,
    )


def info_block(text: str) -> None:
    st.markdown(f'<div class="info-blk">{text}</div>', unsafe_allow_html=True)


def warn_block(text: str) -> None:
    st.markdown(f'<div class="warn-blk">{text}</div>', unsafe_allow_html=True)


def ok_block(text: str) -> None:
    st.markdown(f'<div class="ok-blk">{text}</div>', unsafe_allow_html=True)


def ai_box(text: str, label: str = "AI Analysis") -> None:
    st.markdown(
        f"""<div class="ai-box">
              <div class="ai-lbl">{label}</div>
              <div class="ai-txt">{text}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def table_wrap(rows_html: str, caption: str = "", caption_right: str = "") -> None:
    cap_html = (
        f'<div class="tbl-cap"><span>{caption}</span><span style="color:#2d3f5a;">{caption_right}</span></div>'
        if caption else ""
    )
    st.markdown(
        f'<div class="tbl-wrap">{cap_html}'
        f'<div style="overflow-x:auto;">{rows_html}</div></div>',
        unsafe_allow_html=True,
    )


def score_bar(score: float, width: int = 120) -> str:
    """Return HTML for a glowing score progress bar"""
    col  = score_color(score)
    glow = score_glow(score)
    pct  = min(100, max(0, score))
    grad = {
        "#22c55e": "linear-gradient(90deg, #15803d, #22c55e)",
        "#3b82f6": "linear-gradient(90deg, #1d4ed8, #3b82f6)",
        "#f59e0b": "linear-gradient(90deg, #b45309, #f59e0b)",
        "#ef4444": "linear-gradient(90deg, #991b1b, #ef4444)",
    }.get(col, f"linear-gradient(90deg, {col}, {col})")

    return (
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<div class="score-bar-wrap" style="width:{width}px;">'
        f'<div class="score-bar-fill" style="width:{pct}%;background:{grad};'
        f'box-shadow:0 0 6px {glow};"></div>'
        f'</div>'
        f'<span style="font-family:\'IBM Plex Mono\',monospace;font-size:0.73rem;'
        f'font-weight:600;color:{col};min-width:2.2rem;text-align:right;">'
        f'{score:.0f}</span></div>'
    )


# ── Pandas Styler helpers ─────────────────────────────────────────────────────

def style_pct_col(val):
    try:
        v = float(val)
        if v > 0: return "color:#22c55e"
        if v < 0: return "color:#ef4444"
    except (TypeError, ValueError):
        pass
    return "color:#475569"


def style_score_col(val):
    try:
        v = float(val)
        return f"color:{score_color(v)};font-weight:600"
    except (TypeError, ValueError):
        return "color:#475569"


def base_table_style(df: pd.DataFrame) -> "pd.io.formats.style.Styler":
    return (
        df.style
        .set_properties(**{
            "background-color": "#0a1020",
            "color": "#64748b",
            "border-color": "#141e30",
            "font-size": "0.76rem",
            "font-family": "'IBM Plex Mono', monospace",
            "padding": "0.42rem 0.8rem",
        })
        .set_table_styles([
            {"selector": "thead th", "props": [
                ("background-color", "#07101e"),
                ("color", "#3d5270"),
                ("font-size", "0.59rem"),
                ("text-transform", "uppercase"),
                ("letter-spacing", "0.09em"),
                ("font-family", "'IBM Plex Sans', sans-serif"),
                ("font-weight", "700"),
                ("border-bottom", "1px solid #141e30"),
                ("padding", "0.5rem 0.8rem"),
            ]},
            {"selector": "tbody tr:hover td", "props": [("background-color", "#0f1929")]},
            {"selector": "tbody tr", "props": [("border-bottom", "1px solid #0c1825")]},
        ])
    )
