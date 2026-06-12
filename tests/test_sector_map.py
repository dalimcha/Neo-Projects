import pandas as pd
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ALLOWED = {
    "Defence", "Railways", "Capital Goods", "Power & Utilities", "T&D",
    "Infra EPC", "Renewables", "Shipbuilding", "EMS", "Industrial Manufacturing",
    "Banks", "NBFCs", "IT Services", "Pharma", "Hospitals", "Cement", "Metals",
    "Autos", "Real Estate", "Consumer", "Chemicals", "Logistics", "Hotels",
    "Telecom", "Media", "Oil & Gas", "Financial Services", "Electronics",
    "Construction Materials", "Services", "Healthcare",
}


def test_sector_map_covers_universe_without_other():
    universe = pd.read_csv(ROOT / "data" / "universe.csv")
    sector_map = pd.read_csv(ROOT / "data" / "sector_map.csv")
    merged = universe[["ticker"]].merge(sector_map[["ticker", "sector"]], on="ticker", how="left")
    assert merged["sector"].notna().all()
    assert not merged["sector"].astype(str).str.contains("Other", case=False, na=False).any()
    assert set(merged["sector"].dropna().astype(str)).issubset(ALLOWED)
