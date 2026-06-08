import sqlite3
import pandas as pd
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "secondaries.db")

NA_MARKERS = {
    "NOT_AVAILABLE_PUBLICLY", "SUBSCRIPTION_REQUIRED", "TOO_YOUNG_TO_EVALUATE",
    "NEEDS_MANUAL_REVIEW", "STALE", "MANAGER_REPORTED", "LP_REPORTED", "NOT_AVAILABLE"
}


def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS funds (
        fund_id TEXT PRIMARY KEY,
        gp_name TEXT,
        fund_name TEXT,
        short_name TEXT,
        vintage_year INTEGER,
        fund_size_usd_bn REAL,
        target_size_usd_bn TEXT,
        percent_above_target TEXT,
        final_close_year TEXT,
        final_close_date TEXT,
        status TEXT,
        strategy_type TEXT,
        geography TEXT,
        asset_class TEXT,
        lp_led_focus TEXT,
        gp_led_focus TEXT,
        single_asset_cv_focus TEXT,
        private_wealth_channel TEXT,
        co_investment_or_overflow TEXT,
        source_url TEXT,
        source_type TEXT,
        source_confidence TEXT,
        notes TEXT,
        last_updated TEXT,
        neo_takeaway TEXT
    );

    CREATE TABLE IF NOT EXISTS performance (
        performance_id TEXT PRIMARY KEY,
        fund_id TEXT,
        as_of_date TEXT,
        committed_usd_m REAL,
        contributed_usd_m REAL,
        distributed_usd_m REAL,
        market_value_usd_m REAL,
        net_irr_pct TEXT,
        gross_irr_pct TEXT,
        dpi TEXT,
        rvpi TEXT,
        tvpi TEXT,
        moic TEXT,
        pme TEXT,
        reported_by TEXT,
        source_url TEXT,
        source_document_name TEXT,
        source_type TEXT,
        confidence_level TEXT,
        performance_scope TEXT,
        notes TEXT,
        irr_flag TEXT,
        dpi_flag TEXT,
        tvpi_flag TEXT,
        FOREIGN KEY (fund_id) REFERENCES funds(fund_id)
    );

    CREATE TABLE IF NOT EXISTS deals (
        deal_id TEXT PRIMARY KEY,
        fund_id TEXT,
        deal_name TEXT,
        deal_type TEXT,
        seller_or_sponsor TEXT,
        underlying_company_or_fund TEXT,
        sector TEXT,
        geography TEXT,
        transaction_size_usd_m TEXT,
        entry_discount_or_premium TEXT,
        date_announced TEXT,
        date_closed TEXT,
        source_url TEXT,
        confidence_level TEXT,
        notes TEXT,
        FOREIGN KEY (fund_id) REFERENCES funds(fund_id)
    );

    CREATE TABLE IF NOT EXISTS lp_commitments (
        commitment_id TEXT PRIMARY KEY,
        fund_id TEXT,
        lp_name TEXT,
        lp_type TEXT,
        commitment_amount_usd_m REAL,
        commitment_date TEXT,
        source_url TEXT,
        confidence_level TEXT,
        notes TEXT,
        FOREIGN KEY (fund_id) REFERENCES funds(fund_id)
    );

    CREATE TABLE IF NOT EXISTS alerts (
        alert_id TEXT PRIMARY KEY,
        fund_id TEXT,
        alert_date TEXT,
        alert_type TEXT,
        summary TEXT,
        importance TEXT,
        recommended_action TEXT,
        source_url TEXT,
        FOREIGN KEY (fund_id) REFERENCES funds(fund_id)
    );

    CREATE TABLE IF NOT EXISTS sources (
        source_id TEXT PRIMARY KEY,
        fund_id TEXT,
        source_date TEXT,
        source_type TEXT,
        source_name TEXT,
        source_url TEXT,
        data_items_covered TEXT,
        confidence_level TEXT,
        subscription_required TEXT,
        analyst_notes TEXT,
        last_checked TEXT
    );
    """)
    conn.commit()
    conn.close()


NEO_TAKEAWAYS = {
    "Ardian": (
        "Data discipline and systematic LP relationship mapping are world-class. "
        "Copy the diversified secondaries underwriting process and portfolio construction rigor. "
        "Do not copy mega-scale strategy — $19–30bn funds require global placement infrastructure "
        "Neo cannot replicate. Avoid brand-over-substance fundraising. "
        "Relevance to Indian family office clients: use Ardian's LP-mix transparency as a benchmark "
        "for how Neo should present fund governance to HNI/UHNI LPs."
    ),
    "Lexington Partners": (
        "Repeatable, institutional underwriting process and diversified secondaries discipline. "
        "Copy their vintage-year diversification framework and LP onboarding documentation quality. "
        "Lexington's private wealth channel expansion (LCP X onward) is directly relevant for Neo. "
        "Avoid over-reliance on relationship-driven deal sourcing without underwriting depth. "
        "Relevance to Indian family office clients: Lexington's democratization of secondaries "
        "through smaller commitment sizes is the right model for Neo's HNI access strategy."
    ),
    "Blackstone Strategic Partners": (
        "Platform integration, GP access, and data infrastructure are best-in-class. "
        "Copy the GP-led overlay strategy (SP GPS alongside SP IX) and the institutional data room culture. "
        "Monitor conflicts between Blackstone as GP and Blackstone Strategic Partners as secondaries buyer. "
        "Monitor scale risk — $22bn funds create adverse selection at smaller deal sizes. "
        "Relevance to Indian family office clients: Blackstone's private wealth push and "
        "feeder structures are a template Neo can adapt for GIFT City or SEBI AIF structures."
    ),
    "HarbourVest Partners": (
        "Overflow co-investment structure (DS XI + $3.4bn overflow) is directly copyable for Neo. "
        "Copy the dual-vehicle approach that separates core secondaries from co-investment overflow. "
        "HarbourVest's primary + secondary + co-investment integration is the fullest expression "
        "of the multi-strategy private markets platform. "
        "Relevance to Indian family office clients: overflow structures allow smaller LP tickets "
        "into specific deals — ideal for Indian family office club deal culture."
    ),
    "Coller Capital": (
        "Specialist secondaries identity and brand consistency over 30+ years. "
        "Copy the dedicated secondaries focus without style drift into primary PE or co-investments. "
        "Coller's LP-led and GP-led balance (CIP IX) shows that specialists can do both without losing identity. "
        "Avoid Coller's opacity on fund-level performance — Neo should be more transparent with LPs. "
        "Relevance to Indian family office clients: specialist positioning is easier to explain "
        "and sell to sophisticated UHNI clients than a blended multi-strategy fund."
    ),
    "Carlyle AlpInvest": (
        "Institutional-quality secondaries underwriting packaged for private wealth access. "
        "Copy the hard-cap discipline combined with separate private wealth co-investment vehicles. "
        "AlpInvest's Carlyle backing provides GP access Neo cannot replicate, but the "
        "underwriting documentation culture is learnable. "
        "Relevance to Indian family office clients: AlpInvest's private wealth channel is the "
        "closest structural analog to what Neo is building — adapt their LP reporting standards."
    ),
    "Goldman Sachs Asset Management": (
        "Distribution and investor education engine is unmatched for private wealth. "
        "Copy Goldman's structured education program and standardized LP reporting. "
        "Avoid brand-only selling — Goldman's IRR claims need DPI verification just like any other manager. "
        "The Vintage IX $14.2bn close above target reflects Goldman's distribution advantage, not necessarily "
        "superior underwriting. "
        "Relevance to Indian family office clients: Goldman's private wealth education materials "
        "are a template Neo can adapt for Indian HNI financial literacy in secondaries."
    ),
    "ICG Strategic Equity": (
        "GP-led and single-asset continuation vehicle underwriting discipline is best-in-class among specialists. "
        "Copy ICG's rigorous single-asset underwriting checklist and GP alignment verification process. "
        "ICG's more-than-doubling of fund size (ICGSE V vs ICGSE IV) reflects market demand shift toward GP-led. "
        "Monitor GP-led concentration risk — single-asset CVs carry binary outcome risk. "
        "Relevance to Indian family office clients: GP-led CVs are an underpenetrated secondaries category "
        "in India — ICG's framework is directly applicable to Neo's Indian GP relationship network."
    ),
}


def seed_funds():
    conn = get_conn()
    existing = pd.read_sql("SELECT fund_id FROM funds", conn)
    if len(existing) > 0:
        conn.close()
        return

    csv_path = os.path.join(os.path.dirname(__file__), "seed_funds.csv")
    df = pd.read_csv(csv_path)

    for gp, takeaway in NEO_TAKEAWAYS.items():
        df.loc[df["gp_name"] == gp, "neo_takeaway"] = takeaway

    df.to_sql("funds", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()


def _compute_perf_flags(row):
    def is_numeric(v):
        try:
            float(v)
            return True
        except (ValueError, TypeError):
            return False

    irr_flag = ""
    dpi_flag = ""
    tvpi_flag = ""

    net_irr = row.get("net_irr_pct", "")
    dpi = row.get("dpi", "")
    tvpi = row.get("tvpi", "")
    rvpi = row.get("rvpi", "")

    irr_num = float(net_irr) if is_numeric(net_irr) else None
    dpi_num = float(dpi) if is_numeric(dpi) else None
    tvpi_num = float(tvpi) if is_numeric(tvpi) else None

    vintage = row.get("vintage_year")
    current_year = 2026
    fund_age = (current_year - int(vintage)) if vintage and str(vintage).isdigit() else None

    if fund_age is not None and fund_age <= 3:
        irr_flag = "TOO_YOUNG — IRR not meaningful"
    elif irr_num is not None and dpi_num is not None:
        if irr_num > 20 and dpi_num < 0.3:
            irr_flag = "HIGH PAPER IRR — cash realization limited"
        elif irr_num > 15 and dpi_num < 0.5:
            irr_flag = "INTERIM IRR — moderate DPI; monitor realization"

    if dpi_num is not None:
        if dpi_num >= 1.0:
            dpi_flag = "CAPITAL SUBSTANTIALLY RETURNED"
        elif dpi_num < 0.2:
            dpi_flag = "LOW DPI — realization risk"
        elif dpi_num < 0.5:
            dpi_flag = "MODERATE DPI — still mostly unrealized"

    if tvpi_num is not None and dpi_num is not None:
        if tvpi_num > 1.5 and dpi_num < 0.5:
            tvpi_flag = "NAV-HEAVY — realization risk remains"
        elif tvpi_num > 1.5 and dpi_num >= 1.0:
            tvpi_flag = "STRONG TVPI WITH SOLID DPI"

    return irr_flag, dpi_flag, tvpi_flag


def seed_performance():
    conn = get_conn()
    existing = pd.read_sql("SELECT performance_id FROM performance", conn)
    if len(existing) > 0:
        conn.close()
        return

    csv_path = os.path.join(os.path.dirname(__file__), "seed_performance.csv")
    df = pd.read_csv(csv_path, dtype=str)

    funds_df = pd.read_sql("SELECT fund_id, vintage_year FROM funds", conn)
    df = df.merge(funds_df, on="fund_id", how="left")

    flags = df.apply(_compute_perf_flags, axis=1)
    df["irr_flag"] = [f[0] for f in flags]
    df["dpi_flag"] = [f[1] for f in flags]
    df["tvpi_flag"] = [f[2] for f in flags]

    df = df.drop(columns=["vintage_year"], errors="ignore")
    df.to_sql("performance", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()


def seed_sources():
    conn = get_conn()
    existing = pd.read_sql("SELECT source_id FROM sources", conn)
    if len(existing) > 0:
        conn.close()
        return

    csv_path = os.path.join(os.path.dirname(__file__), "seed_sources.csv")
    df = pd.read_csv(csv_path)
    df.to_sql("sources", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()


def get_funds_df():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM funds ORDER BY fund_size_usd_bn DESC", conn)
    conn.close()
    return df


def get_performance_df():
    conn = get_conn()
    df = pd.read_sql("""
        SELECT p.*, f.gp_name, f.fund_name, f.short_name, f.vintage_year, f.strategy_type
        FROM performance p
        LEFT JOIN funds f ON p.fund_id = f.fund_id
        ORDER BY p.as_of_date DESC
    """, conn)
    conn.close()
    return df


def get_deals_df():
    conn = get_conn()
    df = pd.read_sql("""
        SELECT d.*, f.gp_name, f.fund_name
        FROM deals d
        LEFT JOIN funds f ON d.fund_id = f.fund_id
        ORDER BY d.date_closed DESC
    """, conn)
    conn.close()
    return df


def get_lp_commitments_df():
    conn = get_conn()
    df = pd.read_sql("""
        SELECT lp.*, f.gp_name, f.fund_name
        FROM lp_commitments lp
        LEFT JOIN funds f ON lp.fund_id = f.fund_id
        ORDER BY lp.commitment_date DESC
    """, conn)
    conn.close()
    return df


def get_alerts_df():
    conn = get_conn()
    df = pd.read_sql("""
        SELECT a.*, f.gp_name, f.fund_name
        FROM alerts a
        LEFT JOIN funds f ON a.fund_id = f.fund_id
        ORDER BY a.alert_date DESC
    """, conn)
    conn.close()
    return df


def get_sources_df():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM sources ORDER BY last_checked DESC", conn)
    conn.close()
    return df


def upsert_fund(data: dict):
    conn = get_conn()
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?" for _ in data])
    updates = ", ".join([f"{k}=excluded.{k}" for k in data if k != "fund_id"])
    sql = f"INSERT INTO funds ({cols}) VALUES ({placeholders}) ON CONFLICT(fund_id) DO UPDATE SET {updates}"
    conn.execute(sql, list(data.values()))
    conn.commit()
    conn.close()


def upsert_performance(data: dict):
    conn = get_conn()
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?" for _ in data])
    updates = ", ".join([f"{k}=excluded.{k}" for k in data if k != "performance_id"])
    sql = f"INSERT INTO performance ({cols}) VALUES ({placeholders}) ON CONFLICT(performance_id) DO UPDATE SET {updates}"
    conn.execute(sql, list(data.values()))
    conn.commit()
    conn.close()


def insert_alert(fund_id, alert_type, summary, importance, recommended_action, source_url=""):
    conn = get_conn()
    alert_id = f"A{datetime.now().strftime('%Y%m%d%H%M%S')}"
    conn.execute("""
        INSERT OR IGNORE INTO alerts (alert_id, fund_id, alert_date, alert_type, summary, importance, recommended_action, source_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, [alert_id, fund_id, datetime.now().strftime("%Y-%m-%d"), alert_type, summary, importance, recommended_action, source_url])
    conn.commit()
    conn.close()


def import_csv_to_table(csv_path: str, table: str, if_exists: str = "append"):
    df = pd.read_csv(csv_path, dtype=str)
    conn = get_conn()
    df.to_sql(table, conn, if_exists=if_exists, index=False)
    conn.commit()
    conn.close()
    return len(df)


def setup():
    init_db()
    seed_funds()
    seed_performance()
    seed_sources()


if __name__ == "__main__":
    setup()
    print("Database initialized and seeded.")
