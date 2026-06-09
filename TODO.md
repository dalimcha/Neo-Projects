# India Public Markets Intelligence Terminal — TODO

Single source of truth for what's done, what's broken, and what's next.
Update this every time something changes.

---

## ✅ Done (this pass)

### Phase 1 — Data reliability foundation
- [x] `utils/validation.py` — `UniverseReport`, `build_universe_report`, per-analytic gates (`breadth`, `top_movers`, `volume_shocks`, `52w_extremes`, `sector_heatmap`, `ai_summary`)
- [x] `utils/source_helpers.py` — `SourceTag`, `safe_div`, `safe_pct_change`, no more `inf`
- [x] Data Quality Panel — full banner on Command Center + compact sidebar version
- [x] `data/data_quality_log.csv` — every page load appends a snapshot
- [x] `scripts/update_universe.py` — fetches official NSE Nifty 50/100/Next50/500 constituent CSVs

### Critical bug fixes (from live audit)
- [x] A/D ratio: returns `"N/A"` when decliners = 0 (was: `inf`)
- [x] `page_header()` no longer shows fake "Live" — only shows `data_status` when caller passes real freshness
- [x] `index_card()` handles missing data: shows `N/A` and "Data not available", not blank cards
- [x] Index value CSS — `white-space: nowrap` + ellipsis to prevent wrap
- [x] Sensex auto-hides when feed returns no value (was: blank card)
- [x] Home page "System Online" replaced with neutral "Page rendered HH:MM"
- [x] Breadth / movers / heatmap won't render unless the universe passes the validation gate

### Workflow seed data
- [x] `data/research_queue.csv` — schema + 3 seed rows (LT, HAL, MAZDOCK)
- [x] `data/watchlists.csv` — 7 thematic lists pre-populated (Boss Ideas, OB Mispricing, Defence, Railways, Cap Goods, Power T&D, EMS)
- [x] `data/failed_tickers.csv` — schema ready for ingestion failures

---

## 🔴 CRITICAL — required before showing the boss

These are the gating items that make the difference between "demo" and "useful tool":

- [ ] **Run `python scripts/update_universe.py --index 50,100,Next50,500`** locally — pulls all ~500 NSE constituents into `data/universe.csv`. Until this is done, the Nifty 500 validation gate will fail and analytics will refuse to render (which is the correct behaviour).
- [ ] **Run `python scripts/update_prices.py --yf`** locally — populates `prices.csv` with 1Y of history for every ticker in the universe. Without this, no breadth/movers can compute.
- [ ] Commit + push the resulting CSVs to GitHub so Streamlit Cloud picks them up.
- [ ] Add `ANTHROPIC_API_KEY` and `TERMINAL_PASSWORD` as Streamlit Cloud secrets so the boss-facing URL is gated.

---

## Phase 2 — Data pipeline (partial)

- [x] `update_universe.py` (new — Phase 1)
- [x] `update_prices.py` (exists)
- [x] `update_filings.py` (exists)
- [x] `update_fundamentals.py` — write a Screener-CSV → fundamentals.csv normaliser
- [ ] `update_news.py` — pluggable RSS / API ingestion; for now `news.csv` is manual upload only
- [ ] `extract_order_book.py` — PDF / concall transcript → structured row with `source_document`, `page`, `snippet`, `confidence`. Right now order book rows are typed by hand.
- [x] `generate_ai_summaries.py` (exists)
- [x] `send_daily_email.py` (exists)

---

## Phase 4 — Market Command Center additions

- [x] Data Quality banner
- [x] Index Snapshot — auto-hides missing indices
- [x] Market Breadth — gated by validation, no more inf
- [ ] **Today's Market Narrative** — needs an `ai_helpers.market_narrative()` builder that only runs when `gate(rep, "ai_summary")` is True
- [ ] **Meeting Talking Points** — 3 market + 3 sector + 3 stock + 3 questions
- [ ] **Top Movers — actionability tags** — News-driven / Result-driven / Sector move / Technical breakout / Reversal / Needs research / No clear catalyst. Right now movers show price + volume only.
- [x] Volume Shocks (exists)
- [x] 52-Week Extremes (exists)
- [x] Sector Heatmap (exists, now gated)
- [ ] "What Changed Today" — combine price moves + news + filings + OB updates into one feed

---

## Phase 5 — All Companies page

- [ ] Add columns currently missing: `dist_52w_high`, `dist_52w_low`, `volume_vs_30d_avg`, `latest_filing_date`, `latest_result_date`, `trend_classification`, `research_status`
- [ ] Add filter: "Order-book data available"
- [ ] Buttons: "Add to watchlist" / "Add to research queue" — write to the new CSVs
- [ ] Sticky header

## Phase 6 — Company Detail page

- [x] Existing tabs: Overview / Financials / Quarterly / Valuation / Order Book / News & Filings / AI Note / Notes
- [ ] Section 1 expansion: revenue mix / geography / key customers (requires data — schema only for now)
- [ ] Section 3: 5Y valuation range
- [ ] Section 7: structured AI note format (bull case / bear case / what to track / questions)

## Phase 7 — Order Book Screener (flagship)

- [x] 6-factor scoring model (exists)
- [x] Source traceability fields (exists)
- [ ] Add penalties listed in spec but not yet wired: receivables_growth, customer_concentration, one_off_order, stale_OB_data (>180d old)
- [ ] Classification: rename "Buy/Sell" — confirmed none, but verify all UI text says "research candidate" / "watchlist" / "avoid"
- [ ] New charts: Score vs valuation, Score vs 1Y return, Confidence distribution

## Phase 8 — New Ideas Engine

- [x] Basic flag rules (exists: OB > 2x rev, OB > MCap, etc.)
- [ ] Add rules: positive_filing + volume_shock, margin_expansion, revenue_acceleration, promoter_buying, FII/DII accumulation
- [ ] Buttons on each idea card: "Add to Research Queue" / "Add to Watchlist" / "Mark rejected" — wire to CSVs

## Phase 9 — News & Filings

- [x] Page exists with NSE corp announcements
- [ ] Materiality score column
- [ ] Watchlist-only filter
- [ ] Order-book-related-only filter
- [ ] AI summary format upgrade per spec

## Phase 10 — Sector Intelligence

- [x] 5 sectors with deep content (Cap Goods, Power, IT, Healthcare, Fin Svcs)
- [ ] Add the remaining 16: Railways, Defence, Power T&D, Infra EPC, Renewables, EMS, Banks, NBFCs, Pharma, Hospitals, Cement, Metals, Autos, Real Estate, Consumer, Chemicals, Logistics, Hotels, Telecom
- [ ] For each: cycle position, demand/margin drivers, quality vs momentum lists, mispricing candidates

## Phase 11 — Research Queue (NEW PAGE)

- [ ] Build `pages/8_Research_Queue.py` reading `data/research_queue.csv`
- [ ] CRUD: add note, move status, change priority
- [ ] "Generate company one-pager" button → exports PDF
- [ ] "Generate boss update" button → templated email draft

## Phase 12 — Watchlists (NEW PAGE)

- [ ] Build `pages/9_Watchlists.py` reading `data/watchlists.csv`
- [ ] Per-list view: latest price move + latest news/filing + last reviewed
- [ ] Add/remove from a list

## Phase 13 — Learning Mode (NEW PAGE)

- [ ] Build `pages/10_Learning_Mode.py`
- [ ] Daily 3 large + 3 mid + 3 small + 1 OB + 1 sector lead + 1 mover assignment
- [ ] 10-minute primer template per company
- [ ] 5-question quiz, persisted score in `data/learning_scores.csv`

## Phase 14 — Daily Email Brief (exists; needs spec upgrade)

- [x] `scripts/send_daily_email.py` — sends morning + evening briefs
- [ ] Morning template upgrade: Global cues / Indian setup / Results today / Board meetings / Yesterday's filings / Stocks to watch / OB names / New ideas / 5 things to know
- [ ] Evening template upgrade: matching spec format

## Phase 15 — Exports & Meeting Prep

- [ ] `utils/export_helpers.py` — PDF generator via `reportlab` or `weasyprint`
- [ ] "Generate 5-minute Meeting Brief" button on Command Center
- [ ] "Generate Boss Update Email" button on Research Queue
- [ ] "Generate Company One-Pager" button on Company Detail

## Phase 16 — UI polish

- [x] Bloomberg-style dark palette
- [x] Compact KPI cards
- [x] Dense tables via custom `<table class='trm'>`
- [x] Fixed index-value wrapping
- [x] Restrained blue accent, no neon
- [ ] Reduce some heading sizes further (h1 → 1.0rem)
- [ ] Sticky table headers (CSS `position:sticky`)
- [ ] Add download CSV buttons on every table

## Phase 17 — Error handling

- [x] `safe_div`, `safe_pct_change` — divide-by-zero returns N/A
- [x] Universe validation gate
- [x] `failed_tickers.csv` schema
- [ ] `data_quality_log.csv` rotation (keep last 30 days)
- [ ] Cached data labelled visibly when serving from cache

## Phase 18 — Documentation

- [x] README exists
- [x] TODO.md (this file)
- [ ] Update README with new validation layer, sources, deployment notes
- [ ] Sample files: already present (universe.csv, prices.csv, order_book.csv, fundamentals.csv, filings.csv, news.csv)

---

## Self-audit checklist (per spec)

| Question | Status |
|----------|--------|
| Does Nifty 500 actually load at least 450 companies? | ❌ Pending — run `update_universe.py` |
| Are top movers calculated from the real loaded universe? | ⚠️ Gated — won't render until universe is full |
| Are all index values sourced and timestamped? | ✅ Yes (`index_card` now takes `source` + `data_ts`) |
| Are missing values handled as N/A? | ✅ `safe_div`, `na()` rendering |
| Is the A/D ratio fixed? | ✅ Returns `"N/A"`, never `inf` |
| Is raw HTML removed? | ⚠️ Need full sweep — most cleared this pass |
| Does the Order Book Screener avoid hallucinated data? | ✅ `manually_verified` flag enforced; AI extraction stamps `manually_verified=False` |
| Does every order-book value have a source and confidence score? | ✅ `source_document`, `source_date`, `extracted_text`, `confidence_score` all required |
| Can I generate a meeting brief? | ❌ Phase 15 pending |
| Can I add companies to a research queue? | ⚠️ CSV exists; UI button still pending (Phase 11) |
| Can I export data? | ⚠️ Partial — Companies page has CSV download; PDF export pending |

---

## Next session priority order

1. **You** run `update_universe.py` + `update_prices.py --yf`, commit, push. This is the gating step.
2. Build `pages/8_Research_Queue.py` and `pages/9_Watchlists.py` (Phases 11–12)
3. Add actionability tags + catalyst column to Top Movers (Phase 4 finish)
4. Wire "Add to research queue" / "Add to watchlist" buttons across Company Detail, Order Book Screener, New Ideas (Phases 5/7/8)
5. Build `export_helpers.py` for Meeting Brief PDF (Phase 15)
6. Add 12 more sector pages (Phase 10)
7. Build Learning Mode (Phase 13)
