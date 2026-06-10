"""Step 0.3 — extract calibration CaCO3 labels from the lab Excel into labels.csv.

The raw workbook (``Auswertung TG-FTIR-ATR-Kalibrierung.xlsx``) is gitignored, so
this script is the *provenance record*: it documents exactly which sheet + column
each committed label came from. Run it to (re)generate ``data/labels.csv``.

Reference value (decided in 0.3): **FTIR CaCO3** = CaCO3 derived from the
evolved-CO2 peak area. Chosen because the workbook's "IN QUANT" block shows these
were the concentrations fed into OPUS Quant — i.e. the apples-to-apples target for
reproducing the paper. (TG-mass-loss CaCO3 in col W agrees to ~1-2 wt%; the nominal
recipe % in cols S/T are targets, not measurements.)

Caveat: a newer post-thesis workbook (Berechnung CO2-Uptake.xlsx) has slightly
different CaCO3 values made for the publication, but the OPUS PLS models were not
retrained on them — so these calibration values are correct. See design-tree.md 0.3.
"""

from __future__ import annotations

import csv
from pathlib import Path

import openpyxl

# Repo-relative paths so the script runs from anywhere.
ROOT = Path(__file__).resolve().parent.parent
XLSX = ROOT / "data" / "Auswertung TG-FTIR-ATR-Kalibrierung.xlsx"
OUT = ROOT / "data" / "labels.csv"

# 0-based column indices in the right-hand summary table (one clean row per sample).
COL_PROBE = 17   # R: sample number 1..12
COL_FTIR = 20    # U: FTIR CaCO3 / %  <- our label
COL_FTIR_ERR = 21  # V: FTIR error / % -- used only to locate the right table


def extract_labels() -> list[tuple[str, float]]:
    """Return ``[('JK_MV_01', 2.45), ...]`` for the 12 calibration samples.

    Anchoring: several blocks in the sheet number rows 1..12 (the summary table and
    the "IN QUANT" copy-lists). Only the summary table carries a per-sample FTIR
    *error* (col V), so we read the first run of integer Probe rows that also have a
    V value — that uniquely picks the summary table without hard-coding row numbers.
    """
    wb = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)
    ws = wb.active

    labels: list[tuple[str, float]] = []
    for row in ws.iter_rows(values_only=True):
        probe = row[COL_PROBE] if len(row) > COL_PROBE else None
        ftir = row[COL_FTIR] if len(row) > COL_FTIR else None
        err = row[COL_FTIR_ERR] if len(row) > COL_FTIR_ERR else None

        # summary-table row = integer probe 1..12 that also has an FTIR error
        if isinstance(probe, int) and 1 <= probe <= 12 and isinstance(err, float):
            sample = f"JK_MV_{probe:02d}"  # matches loader.group_replicates keys
            labels.append((sample, float(ftir)))
        if len(labels) == 12:
            break  # first complete run is the summary table; later blocks repeat

    if len(labels) != 12:
        raise RuntimeError(f"expected 12 calibration labels, got {len(labels)}: {labels}")
    return labels


def main() -> None:
    labels = extract_labels()
    with OUT.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sample", "caco3_wt_pct"])  # FTIR-derived, see module docstring
        writer.writerows((s, round(v, 4)) for s, v in labels)
    print(f"wrote {len(labels)} labels -> {OUT.relative_to(ROOT)}")
    for s, v in labels:
        print(f"  {s}: {v:6.2f} wt%")


if __name__ == "__main__":
    main()
