# Neo Secondaries Intelligence Platform

**Internal Research Tool — Neo Multi Family Office**

An institutional-quality private markets intelligence platform for tracking the largest global private equity secondaries funds, analyzing performance quality, mapping competitive strategy, and building Neo's own secondaries playbook.

---

## What the Platform Does

| Page | Function |
|---|---|
| Executive Brief | Landing page: KPI summary, market signals, watchlist, strategic read |
| Fund Universe | Full fund table with filters, size charts, strategy map |
| Performance Quality | IRR/DPI/TVPI table, scatter analysis, quality flags, source labels |
| Manager Strategy | One card per GP: archetype, edge, risk, Neo copy/avoid, analyst note |
| Market Map | Secondaries sub-strategy definitions, growth drivers, Neo relevance |
| Neo Playbook | Success factors, what Neo should build, IC checklists, mistakes to avoid |
| Source Library | Source registry, confidence rules, data integrity standards |
| Data Import | CSV upload with validation, templates, PitchBook/Preqin import guide |
| Weekly Memo | Structured weekly brief generator with download |

---

## Why This Exists for Neo

Global secondaries managers now raise $10–30bn vehicles. The market has moved beyond discount-to-NAV arbitrage into a multi-strategy institutional category. For Neo to advise family-office clients on secondaries — or to develop its own secondaries capability — it needs:

1. A structured view of the largest global funds and their strategies
2. Clear analysis of performance quality (DPI, not just IRR)
3. A framework for what to copy from established managers and what to avoid
4. India-specific sourcing intelligence
5. Source-tagged data that distinguishes LP-reported from GP-reported from unavailable

This platform is designed for that purpose.

---

## How to Run Locally

```bash
cd Financials
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`.

---

## How to Deploy on Streamlit Cloud

1. Push to GitHub (see git commands below)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Repository: `dalimcha/Neo-Projects`
4. Branch: `main`
5. Main file path: `Financials/app.py`

---

## Folder Structure

```
Financials/
├── app.py                    Main Streamlit app (9 pages)
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml          Dark theme configuration
├── data/
│   ├── funds.csv            15 seeded funds
│   ├── performance.csv      9 CalSTRS LP-reported records
│   ├── manager_profiles.csv 8 GP strategic profiles
│   ├── market_segments.csv  8 secondaries sub-strategies
│   ├── sources.csv          15 source records
│   ├── deals.csv            Empty (import from PitchBook/Preqin)
│   └── lp_commitments.csv   Empty (import from pension reports)
└── utils/
    ├── __init__.py
    ├── styling.py           CSS, palette, HTML render functions
    ├── data_loader.py       CSV loading with path resolution
    ├── analytics.py         Performance flag calculations
    └── memo_generator.py    Weekly brief generator
```

---

## Data Model

### funds.csv
Core fund characteristics: GP, size, vintage, strategy, status, final close, source confidence, strategic archetype, Neo takeaway.

### performance.csv
LP-level capital account data from CalSTRS (June 30, 2025). Includes quality flags, source type, and predecessor benchmark labels.

### manager_profiles.csv
Strategic assessment of 8 GPs: archetype, core edge, risk, what Neo can copy, what to avoid, analyst note.

### market_segments.csv
8 secondaries sub-strategies: definition, growth driver, return driver, key risk, Neo relevance.

### sources.csv
Registry of all data sources with confidence levels and subscription flags.

---

## How to Add New Funds

**Option 1 — Edit CSV directly:**
Open `data/funds.csv` and add a row. Required fields: `fund_id`, `gp_name`, `fund_name`, `vintage_year`, `status`, `source_confidence`, `last_updated`.

**Option 2 — Data Import page:**
Use the Data Import page in the app to upload a CSV with new fund rows. Download the fund template from that page.

**Option 3 — CLI:**
```bash
python update_sources.py fund --id F016 --field fund_size_usd_bn --value 8.5
```

---

## How to Add Performance Data

1. Source the data from CalSTRS, CALPERS, Oregon PERS, or another public LP report
2. Map columns to the performance.csv schema
3. Set `source_type = LP_REPORTED`, `reported_by = [LP name]`, `performance_scope = [LP] LP-level capital account`
4. Set `is_lp_level = Yes`, `is_official_fund_level = No`
5. Use the Data Import page to upload

For fund-level GP performance: set `source_type = MANAGER_REPORTED` and `is_official_fund_level = Yes`. Verify against GP DDQ or official report before marking High confidence.

---

## Why Missing Data Is Explicitly Tagged

A blank field is ambiguous — it could mean zero, unknown, or not applicable. This platform uses explicit unavailability markers:

| Marker | Meaning |
|---|---|
| `NOT_AVAILABLE_PUBLICLY` | Exists but not public |
| `SUBSCRIPTION_REQUIRED` | Available via PitchBook, Preqin, Burgiss |
| `LP_REPORTED_ONLY` | Only available as LP capital account data |
| `MANAGER_REPORTED_ONLY` | Only available from GP |
| `TOO_YOUNG_TO_EVALUATE` | Fund too young for meaningful IRR |
| `NEEDS_MANUAL_REVIEW` | Analyst must verify through primary source |
| `STALE` | Data older than 18 months — re-verify |
| `NOT_MEANINGFUL_YET` | Metric not applicable at current stage |

---

## LP-Reported vs Official Fund-Level Performance

| Dimension | LP-Reported | Manager-Reported (Fund-Level) |
|---|---|---|
| Source | Pension fund capital account (CalSTRS, CalPERS, etc.) | GP fund-level calculation |
| Scope | Single LP's experience | Entire fund |
| Reliability | High — audited LP accounts | Medium — GP methodology may vary |
| Typical use | LP-vs-LP benchmarking | Fund-level comparison |
| Set in tracker | `source_type = LP_REPORTED` | `source_type = MANAGER_REPORTED` |
| Citation | "LP-reported capital account return" | "GP-reported net IRR" |

**Rule:** Never mix LP-reported and manager-reported data in the same comparison without flagging the difference.

---

## How to Use the Weekly Memo

1. Go to the Weekly Memo page
2. Set the as-of date
3. Click Generate Brief
4. Review the output for accuracy before distributing
5. Download as .txt for email distribution

The memo covers: market signal, fundraising updates, performance flags, manual research queue, Neo implications, and analyst action items.

**Automation:** Run `python email_report.py --output report.txt` in a scheduled script for Monday morning delivery.

---

## Known Limitations

- Most fund-level secondaries performance data is private or paywalled. This platform tracks confirmed public data, LP-reported capital account data, manager-reported data, and missing-data gaps separately. It should not be treated as a complete performance database unless supplemented with PitchBook, Preqin, Burgiss, Cambridge Associates, MSCI Private Capital, GP DDQs, or official LP reports.

- All seeded performance data is from CalSTRS LP-level capital accounts as of June 30, 2025. This reflects one LP's experience, not the full fund.

- Predecessor benchmark records (ICG SE III/IV, Coller CIP VI/VII) are historical strategy proxies, not current tracked fund performance.

- Funds in market (LCP XI, SP X, Dover Street XII) have unverified targets — marked NEEDS_MANUAL_REVIEW pending Secondaries Investor/PitchBook verification.

- The app does not scrape live data. All updates are manual via CSV import or direct CSV editing.

---

*Built for Neo Multi Family Office. Confidential — internal use only. Not investment advice.*
