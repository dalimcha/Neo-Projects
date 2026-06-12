import pandas as pd
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QCOLS = [
    "quartile_1m", "quartile_3m", "quartile_6m", "quartile_1y",
    "quartile_3y", "quartile_5y", "quartile_10y",
]


def test_quartiles_are_roughly_balanced_within_sector():
    df = pd.read_csv(ROOT / "data" / "returns_snapshot.csv")
    if "sector" not in df.columns:
        return
    for qcol in QCOLS:
        if qcol not in df.columns:
            continue
        for _, sub in df.groupby("sector"):
            valid = sub[qcol].dropna()
            if len(valid) < 8:
                continue
            expected = len(valid) / 4
            counts = valid.value_counts()
            for q in ["Q1", "Q2", "Q3", "Q4"]:
                assert abs(counts.get(q, 0) - expected) <= 2
