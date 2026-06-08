# Neo Multi Family Office — Secondaries Intelligence Tracker

An internal research tool for tracking the largest global private equity secondaries funds, their strategies, performance, LP commitments, and key deals. Built to help Neo analysts understand what makes a secondaries fund successful and what Neo can implement in its own secondaries strategy.

---

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app initializes and seeds the SQLite database on first run.

---

## What the Tool Does

| Feature | Description |
|---|---|
| Fund Overview | All tracked funds with GP, size, vintage, strategy, status, target, and source confidence |
| Performance Monitor | Net IRR, DPI, RVPI, TVPI with analytical flags and scatter plots |
| Strategy Map | Classify funds by LP-led, GP-led, single-asset CV, private wealth, co-invest/overflow |
| Neo Takeaways | For each GP: what to copy, what to avoid, India family-office relevance |
| LP Commitments & Deals | LP commitment data and secondaries deal data (import from PitchBook/Preqin) |
| Sources & Alerts | Full source registry, subscription flags, manual review queue, analyst alerts |
| Weekly Update Generator | Plain text or HTML email report for Monday morning distribution |
| Data Import | CSV import with column schema guide for PitchBook, Preqin, Burgiss, pension reports |

---

## What Data Is Seeded

### Funds (`seed_funds.csv`)

15 funds across 8 GPs representing the largest global secondaries managers:

| GP | Funds |
|---|---|
| Ardian | ASF VII, ASF VIII, ASF IX |
| Lexington Partners | LCP IX, LCP X, LCP XI (fundraising) |
| Blackstone Strategic Partners | SP VIII, SP IX, SP X (fundraising) |
| HarbourVest Partners | Dover Street XI, Dover Street XII (fundraising) |
| Coller Capital | CIP IX |
| Carlyle AlpInvest | AlpInvest Secondaries Fund VIII |
| Goldman Sachs Asset Management | Vintage Fund IX |
| ICG Strategic Equity | ICGSE V |

Fund sizes range from $11bn (ICG SE V) to $30bn (Ardian ASF IX).

### Performance (`seed_performance.csv`)

9 performance records from **CalSTRS public LP performance table as of June 30, 2025**.

**Critical:** These are LP-level capital account returns for CalSTRS, not fund-level GP performance. They reflect a single LP's experience and may differ from official GP-reported fund returns.

Predecessor funds included for ICG (ICGSE III, ICGSE IV) and Coller (CIP VI, CIP VII) to provide historical strategy benchmarks.

### Sources (`seed_sources.csv`)

15 source records covering GP press releases, Reuters, WSJ, Loyens & Loeff (advisor), CalSTRS LP report, and paywalled news sources.

---

## Why Some Fields Are Marked Unavailable

The tracker uses explicit unavailability markers instead of blanks. A blank would be ambiguous — it could mean zero, unknown, or not applicable. These markers make the distinction clear:

| Marker | Meaning |
|---|---|
| `NOT_AVAILABLE_PUBLICLY` | The data exists but has not been made public |
| `SUBSCRIPTION_REQUIRED` | Available through PitchBook, Preqin, Burgiss, or Secondaries Investor |
| `TOO_YOUNG_TO_EVALUATE` | Fund is too young for meaningful IRR (< 3 years) |
| `NEEDS_MANUAL_REVIEW` | Analyst must verify through a subscription database or primary source |
| `STALE` | Data is older than 12 months; re-verify before citing |
| `MANAGER_REPORTED` | GP-reported figure; verify through LP source if possible |
| `LP_REPORTED` | LP-reported figure; may differ from GP-reported fund-level performance |

---

## How to Update with New Data

### Option 1: CLI

```bash
# Update a single field
python update_sources.py fund --id F001 --field fund_size_usd_bn --value 30.5

# Add a performance data point
python update_sources.py performance --fund-id F001 --irr 27.0 --dpi 0.08 --tvpi 1.22 \
  --reported-by CalSTRS --source-type LP_REPORTED --confidence High

# Import a CSV
python update_sources.py import --table performance --csv /path/to/calstrs_q4_2025.csv

# Create an alert
python update_sources.py alert --fund-id F001 --type "Fund close" --summary "ASF IX final close confirmed at $30bn"
```

### Option 2: Streamlit Data Import Page

Use the **Data Import** page in the app to upload a CSV directly and preview before importing.

### Option 3: SQLite direct

```python
import sqlite3
conn = sqlite3.connect("secondaries.db")
# Use standard SQL
```

---

## How to Import PitchBook / Preqin / Burgiss / Pension CSVs

### PitchBook

Export: Funds → Private Equity Funds → Secondary → apply size/geography filters

Map columns:
- `Fund Name` → `fund_name`
- `Fund Size (USD M)` → `fund_size_usd_bn` (divide by 1000)
- `Vintage Year` → `vintage_year`
- `Fund Status` → `status`
- `Primary Capital Focus` → `strategy_type`

Set: `source_type = SUBSCRIPTION_REQUIRED`, `source_confidence = Medium`

### Preqin

Preqin collects performance data from GPs (manager-reported).

Set: `source_type = MANAGER_REPORTED`, `confidence_level = Medium`

Always fill `performance_scope` with "Preqin manager-reported fund-level".

### Burgiss

Burgiss collects from LP capital accounts — most reliable for fund-level aggregates.

Set: `source_type = LP_REPORTED`, `confidence_level = High`

Fill `performance_scope` with "Burgiss pooled LP universe" or specific LP name.

### Pension LP Reports (CalSTRS, CALPERS, NYCERS, etc.)

1. Download the public performance PDF from the pension website
2. Parse tables manually or with a PDF parser
3. Map to `performance` schema
4. Set `source_type = LP_REPORTED`, `reported_by = [LP Name]`
5. Set `performance_scope = [LP Name] LP-level capital account`

**Key sources:**
- CalSTRS: https://www.calstrs.com/private-equity-portfolio-performance-table
- CALPERS: https://www.calpers.ca.gov/page/investments/asset-classes/private-equity
- Oregon PERS: https://www.oregon.gov/pers/board/pages/investment-reports.aspx
- Washington State Investment Board: https://www.sib.wa.gov/financial/docs/

---

## LP-Reported vs Manager-Reported: How to Distinguish

| Dimension | LP-Reported | Manager-Reported |
|---|---|---|
| Source | Pension fund or LP capital account | GP fund-level performance |
| Scope | Single LP's experience | Entire fund |
| Reliability | High (audited LP accounts) | Medium (GP calculation) |
| Typical bias | May understate fund-level if LP called late | May show gross rather than net |
| Use case | Cross-LP benchmarking | Fund-level comparison |
| How to set in tracker | `source_type = LP_REPORTED` | `source_type = MANAGER_REPORTED` |

**Rule:** Never mix LP-reported and manager-reported data in the same comparison without flagging the difference.

---

## Analytical Rules Built Into the Tool

1. For young funds (< 3 years), IRR is flagged as potentially misleading — flag: `TOO_YOUNG — IRR not meaningful`
2. For secondaries, always analyze IRR with DPI and TVPI together, never IRR alone
3. High IRR + low DPI (< 0.3x): `HIGH PAPER IRR — cash realization limited`
4. High TVPI + low DPI (< 0.5x): `NAV-HEAVY — realization risk remains`
5. DPI ≥ 1.0x: `CAPITAL SUBSTANTIALLY RETURNED`
6. All performance data is labeled by source type and scope

---

## How an Analyst at Neo Should Use This Tool

### Monday Morning Workflow

1. Open the app: `streamlit run app.py`
2. Go to **Weekly Update Generator** → Generate report → Review flags
3. Check **Sources & Alerts** → resolve NEEDS_MANUAL_REVIEW items
4. Check **Performance Monitor** → review any new DPI/TVPI movements
5. Email the generated report to the Neo investment committee

### When Evaluating a New Fund

1. Go to **Fund Overview** → find the fund or its predecessor series
2. Check **Performance Monitor** → compare IRR, DPI, TVPI against peer funds at same vintage age
3. Go to **Neo Takeaways** → review the GP-level analytical framework
4. Go to **Strategy Map** → understand where this fund fits vs Neo's own strategy

### When Updating Data

1. Use the **Data Import** page for bulk updates
2. Use `python update_sources.py` for single-field updates
3. Always set `source_confidence` and `source_type` correctly
4. Always use NA markers for unavailable fields — never leave blank

### What Not to Do

- Do not cite CalSTRS LP-reported returns as official fund performance
- Do not treat a high IRR on a < 3 year old fund as meaningful
- Do not import from subscription sources and set confidence to `High` unless cross-verified
- Do not treat blank fields as zero — always check for NA markers

---

## Database Schema

### funds
Core fund characteristics, fundraising data, strategy classification, and source metadata.

### performance
Historical performance snapshots per fund. Multiple rows allowed per fund (different as_of dates or sources). Includes computed analytical flags for IRR, DPI, TVPI.

### deals
Individual secondaries transactions linked to a fund. Populate from PitchBook, Preqin, or Secondaries Investor.

### lp_commitments
Individual LP commitments to each fund. Populate from pension annual reports, PitchBook, or Preqin.

### alerts
Analyst-created alerts for fund events: new closes, performance updates, data quality issues.

### sources
Registry of all data sources used, with subscription flags and manual review status.

---

## File Structure

```
.
├── app.py               — Streamlit dashboard (8 pages)
├── database.py          — SQLite init, seed, query helpers
├── update_sources.py    — CLI for updating individual records
├── email_report.py      — Weekly email generator (text + HTML)
├── seed_funds.csv       — 15 seeded funds
├── seed_performance.csv — 9 seeded CalSTRS LP performance records
├── seed_sources.csv     — 15 seeded source records
├── requirements.txt     — Python dependencies
├── README.md            — This file
└── secondaries.db       — SQLite database (created on first run)
```

---

## Dependencies

```
streamlit>=1.35.0
pandas>=2.0.0
plotly>=5.18.0
openpyxl>=3.1.0
```

---

## Notes on Data Quality

All performance data in the initial seed is sourced from the **CalSTRS public LP performance table as of June 30, 2025**. This is:
- A single LP's capital account, not a fund-level return
- Public and freely available (no subscription required)
- Appropriate for LP-vs-LP benchmarking and preliminary screening
- **Not appropriate** for citing as official fund performance in investor materials

For fund-level GP performance data, sources include:
- Official GP press releases (High confidence)
- Preqin manager-reported (Medium confidence)
- Burgiss pooled LP universe (High confidence)
- Secondaries Investor / PEI (Medium confidence, subscription required)

---

*Built for Neo Multi Family Office internal research. Not for distribution. Performance data is LP-reported and does not constitute investment advice.*
