"""Step 2.1 — extract external-validation CaCO3 labels into val_labels.csv.

The validation twin of ``extract_labels.py`` (0.3). The raw workbook
(``Berechnung CO2-Uptake.xlsx``) is gitignored, so this script is the provenance
record for the committed ``data/val_labels.csv``.

Reference value: **FTIR CaCO3** (sheet ``TG-FTIR NEU NEU``, col I, under the
``FTIR-Gewichtsanteile / wt.-%`` header) — CaCO3 from the evolved-CO2 peak area,
the same kind of number 0.3 chose for calibration, so cal and val labels are
apples-to-apples.

Aggregation = the paper's 8 Figure-7 points, via ``src.val.figure7_key`` (the same
rule the spectra grouper uses, so labels and spectra can't disagree): V1-V3 keep
each measurement series as its own point; V4/V5 (the precision discs) average their
6 series into one point each; V6/V7 drop out. The earlier build averaged V1-V3's two
series together — that smoothed away the very points Figure 7 plots.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so `from src...` works when run as a plain script

from src.val import figure7_key

XLSX = ROOT / "data" / "Berechnung CO2-Uptake.xlsx"
SHEET = "TG-FTIR NEU NEU"
OUT = ROOT / "data" / "val_labels.csv"

COL_PROBE = 0    # A: series name, e.g. 'JK_V1 (60 Min AKL)' or 'JK_V1_2'
COL_FTIR = 8     # I: FTIR CaCO3 / %  <- our label

# Parse (disc, series) from a TG-FTIR row name: 'JK_V1 (60 Min AKL)' -> (1, 1) (the
# unnumbered first series), 'JK_V1_2' -> (1, 2), 'JK_V4_3' -> (4, 3). The (disc,
# series) then routes through the shared figure7_key, identical to the spectra side.
_PROBE = re.compile(r"JK_V(\d+)(?:_(\d+))?")


def extract_val_labels() -> list[tuple[str, float]]:
    """Return ``[('JK_V1_1', 47.58), ..., ('JK_V4', 47.70), ('JK_V5', 20.22)]``.

    Per-point mean FTIR CaCO3: V1-V3 points are single series (mean of one row);
    V4/V5 points average all 6 precision-series rows (the paper's Figure-7 value).
    """
    wb = openpyxl.load_workbook(XLSX, data_only=True, read_only=True)
    ws = wb[SHEET]

    by_point: dict[str, list[float]] = defaultdict(list)
    for row in ws.iter_rows(values_only=True):
        probe = row[COL_PROBE] if len(row) > COL_PROBE else None
        ftir = row[COL_FTIR] if len(row) > COL_FTIR else None
        if not isinstance(probe, str):
            continue
        m = _PROBE.search(probe)
        # require a real numeric label; skips headers, blanks, and any stray text row
        if m is None or not isinstance(ftir, (int, float)):
            continue
        disc = int(m.group(1))
        series = int(m.group(2)) if m.group(2) else 1
        key = figure7_key(disc, series)
        if key is None:
            continue  # V6 (below cal range) / V7 (optimization sample)
        by_point[key].append(float(ftir))

    # average each point's rows (one row for V1-V3 series, six for V4/V5), key-sorted
    labels = [(key, sum(vals) / len(vals)) for key, vals in sorted(by_point.items())]
    if len(labels) != 8:
        raise RuntimeError(f"expected 8 Figure-7 points, got {len(labels)}: {labels}")
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
