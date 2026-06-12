"""Step 2.1 — extract external-validation CaCO3 labels into val_labels.csv.

The validation twin of ``extract_labels.py`` (0.3). The raw workbook
(``Berechnung CO2-Uptake.xlsx``) is gitignored, so this script is the provenance
record for the committed ``data/val_labels.csv``.

Reference value: **FTIR CaCO3** (sheet ``TG-FTIR NEU NEU``, col I, under the
``FTIR-Gewichtsanteile / wt.-%`` header) — CaCO3 from the evolved-CO2 peak area,
the same kind of number 0.3 chose for calibration, so cal and val labels are
apples-to-apples.

Per-specimen aggregation: each CO2-exposure disc (V1..V6) was measured as several
TG-FTIR aliquots, one row each (``JK_V1``, ``JK_V1_2``, ...). They are aliquots of
the *same* disc, so we average them into one y per specimen — matching the one-row-
per-disc spectra grouping in ``src/val.py``. (Counting aliquots as independent
points would be pseudoreplication.)
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
XLSX = ROOT / "data" / "Berechnung CO2-Uptake.xlsx"
SHEET = "TG-FTIR NEU NEU"
OUT = ROOT / "data" / "val_labels.csv"

COL_PROBE = 0    # A: series name, e.g. 'JK_V1 (60 Min AKL)' or 'JK_V1_2'
COL_FTIR = 8     # I: FTIR CaCO3 / %  <- our label

# JK_V7 appears in this sheet but is NOT a validation specimen: per the lab records
# it was folded into the model for Stage-3 *optimization* (the paper's Table 5 /
# optional step 2.3), not used for external validation (Figure 7). We also have only
# its TG-FTIR, no raw ATR spectra. Excluded so val_labels.csv = the 6 Figure-7 discs.
EXCLUDE = {"JK_V7"}

# Grab the specimen key from a series name, ignoring series suffix + annotations:
# 'JK_V1 (60 Min AKL)' -> 'JK_V1', 'JK_V4_3' -> 'JK_V4'. Same grab-prefix rule the
# spectra grouper uses, so label keys line up with src/val.group_specimens keys.
_SPECIMEN = re.compile(r"JK_V(\d+)")


def extract_val_labels() -> list[tuple[str, float]]:
    """Return ``[('JK_V1', 44.72), ...]`` — per-specimen mean FTIR CaCO3."""
    wb = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)
    ws = wb[SHEET]

    by_specimen: dict[str, list[float]] = defaultdict(list)
    for row in ws.iter_rows(values_only=True):
        probe = row[COL_PROBE] if len(row) > COL_PROBE else None
        ftir = row[COL_FTIR] if len(row) > COL_FTIR else None
        if not isinstance(probe, str):
            continue
        m = _SPECIMEN.search(probe)
        # require a real numeric label; skips headers, blanks, and any stray text row
        if m is None or not isinstance(ftir, (int, float)):
            continue
        key = f"JK_V{m.group(1)}"
        if key in EXCLUDE:
            continue  # V7: optimization sample, not validation (see EXCLUDE comment)
        by_specimen[key].append(float(ftir))

    # average each disc's aliquots, ordered by specimen number for a stable file
    labels = [
        (key, sum(vals) / len(vals))
        for key, vals in sorted(by_specimen.items(), key=lambda kv: int(kv[0][4:]))
    ]
    if len(labels) != 6:
        raise RuntimeError(f"expected 6 validation specimens (V1..V6), got {len(labels)}: {labels}")
    return labels


def main() -> None:
    labels = extract_val_labels()
    with OUT.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sample", "caco3_wt_pct"])  # FTIR-derived, see module docstring
        writer.writerows((s, round(v, 4)) for s, v in labels)
    print(f"wrote {len(labels)} validation labels -> {OUT.relative_to(ROOT)}")
    for s, v in labels:
        print(f"  {s}: {v:6.2f} wt%")


if __name__ == "__main__":
    main()
