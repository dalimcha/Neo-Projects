"""
update_sources.py

CLI utility for adding new data points to the Secondaries Intelligence Tracker.
Run interactively or import and call functions programmatically.

Usage:
    python update_sources.py --help
    python update_sources.py fund --id F001 --field fund_size_usd_bn --value 30.5
    python update_sources.py performance --fund-id F001 --irr 27.0 --dpi 0.08 --tvpi 1.22
    python update_sources.py import --table funds --csv /path/to/new_funds.csv
    python update_sources.py alert --fund-id F001 --type "New close" --summary "ASF IX final close confirmed"
"""

import argparse
import sys
from datetime import datetime
import database as db


def cmd_update_fund(args):
    data = {"fund_id": args.id, args.field: args.value, "last_updated": datetime.now().strftime("%Y-%m-%d")}
    db.upsert_fund(data)
    print(f"Updated {args.id}: {args.field} = {args.value}")


def cmd_update_performance(args):
    perf_id = f"P_{args.fund_id}_{datetime.now().strftime('%Y%m%d')}"
    data = {
        "performance_id": perf_id,
        "fund_id": args.fund_id,
        "as_of_date": args.as_of or datetime.now().strftime("%Y-%m-%d"),
        "net_irr_pct": args.irr or "NOT_AVAILABLE_PUBLICLY",
        "dpi": args.dpi or "NOT_AVAILABLE_PUBLICLY",
        "rvpi": args.rvpi or "NOT_AVAILABLE_PUBLICLY",
        "tvpi": args.tvpi or "NOT_AVAILABLE_PUBLICLY",
        "reported_by": args.reported_by or "NEEDS_MANUAL_REVIEW",
        "source_type": args.source_type or "NEEDS_MANUAL_REVIEW",
        "confidence_level": args.confidence or "Low",
        "performance_scope": args.scope or "NEEDS_MANUAL_REVIEW",
        "notes": args.notes or "",
        "gross_irr_pct": "NOT_AVAILABLE_PUBLICLY",
        "moic": "NOT_AVAILABLE_PUBLICLY",
        "pme": "NOT_AVAILABLE_PUBLICLY",
    }
    db.upsert_performance(data)
    print(f"Added performance record {perf_id} for {args.fund_id}")


def cmd_import(args):
    count = db.import_csv_to_table(args.csv, args.table)
    print(f"Imported {count} rows into {args.table}")


def cmd_alert(args):
    db.insert_alert(
        fund_id=args.fund_id,
        alert_type=args.type,
        summary=args.summary,
        importance=args.importance or "Medium",
        recommended_action=args.action or "Review and update tracker",
        source_url=args.source_url or "",
    )
    print(f"Alert created for {args.fund_id}: {args.summary}")


def main():
    parser = argparse.ArgumentParser(description="Secondaries Intelligence Tracker — data update CLI")
    sub = parser.add_subparsers(dest="command")

    # fund update
    p_fund = sub.add_parser("fund", help="Update a single field on a fund record")
    p_fund.add_argument("--id", required=True, help="fund_id (e.g. F001)")
    p_fund.add_argument("--field", required=True, help="Column name to update")
    p_fund.add_argument("--value", required=True, help="New value")

    # performance update
    p_perf = sub.add_parser("performance", help="Add a performance data point")
    p_perf.add_argument("--fund-id", required=True)
    p_perf.add_argument("--as-of", help="Date (YYYY-MM-DD)")
    p_perf.add_argument("--irr", help="Net IRR %%")
    p_perf.add_argument("--dpi", help="DPI")
    p_perf.add_argument("--rvpi", help="RVPI")
    p_perf.add_argument("--tvpi", help="TVPI")
    p_perf.add_argument("--reported-by", help="Source name")
    p_perf.add_argument("--source-type", help="LP_REPORTED / MANAGER_REPORTED / etc.")
    p_perf.add_argument("--confidence", help="High / Medium / Low")
    p_perf.add_argument("--scope", help="Performance scope description")
    p_perf.add_argument("--notes", help="Free text notes")

    # CSV import
    p_import = sub.add_parser("import", help="Import a CSV into a table")
    p_import.add_argument("--table", required=True, choices=["funds", "performance", "deals", "lp_commitments", "alerts", "sources"])
    p_import.add_argument("--csv", required=True, help="Path to CSV file")

    # alert
    p_alert = sub.add_parser("alert", help="Add an alert")
    p_alert.add_argument("--fund-id", required=True)
    p_alert.add_argument("--type", required=True, help="Alert type")
    p_alert.add_argument("--summary", required=True)
    p_alert.add_argument("--importance", help="High / Medium / Low")
    p_alert.add_argument("--action", help="Recommended action")
    p_alert.add_argument("--source-url", help="Source URL")

    args = parser.parse_args()

    db.setup()

    if args.command == "fund":
        cmd_update_fund(args)
    elif args.command == "performance":
        cmd_update_performance(args)
    elif args.command == "import":
        cmd_import(args)
    elif args.command == "alert":
        cmd_alert(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
