"""Assemble the external-validation set: the paper's 8 Figure-7 points (X, y).

Step 2.1 (rebuilt). The validation mirror of ``dataset.py`` (step 0.4), but
self-contained: the validation OPUS filenames nest one level deeper and
inconsistently (``specimen _ series . repeat``), so this module carries its own
identity rule, averaging, and axis guard rather than bending the calibration code.

The paper's Figure 7 is **8 points**, not 6 discs (confirmed against the lab's
model-evaluation sheet -- see ``figure7_key``):
  * V1, V2, V3 were each measured in **two series**; the paper plots each series as
    its own validation point -> 6 points (``JK_V1_1``, ``JK_V1_2``, ...).
  * V4 and V5 were the *precision* discs (48 & 20 wt%), measured 6x for the F-test;
    the paper plots each as a **single point = the mean of its 6 series** -> 2 points
    (``JK_V4``, ``JK_V5``).
  * V6 is below the calibration range (never validated) and V7 was a Stage-3
    optimization sample -- both excluded.
The earlier one-row-per-disc build averaged V1-V3's two series together, smoothing
away the very points Figure 7 plots; ``figure7_key`` encodes the paper's choice.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from src.dataset import Dataset, read_labels
from src.loader import load_spectrum

# A validation replicate file is  JK_V<disc>[_<series>].<repeat>  with all-numeric
# fields. Group 1 = disc, group 2 = series (absent for each disc's first, unnumbered
# series -> treated as series 1). The anchored pattern requiring a trailing ".<digits>"
# is what drops JK_V2_Test.0 for free: "_Test" is not "_<digits>", so it never matches.
_VAL_FILE = re.compile(r"^JK_V(\d+)(?:_(\d+))?\.\d+$")

# V4/V5 were measured 6x for the precision F-test (48 & 20 wt%); the paper plots each
# as one Figure-7 point = the mean over its series, so we pool all their series.
_PRECISION_DISCS = (4, 5)
# Not external-validation points: V6 sits below the calibration range (never
# validated); V7 was a Stage-3 optimization sample (paper Table 5 / optional 2.3).
_NON_VALIDATION_DISCS = (6, 7)


def figure7_key(disc: int, series: int) -> str | None:
    """Canonical Figure-7 point a (disc, series) belongs to, or ``None`` to drop it.

    The single source of truth for the paper's aggregation choice, shared by the
    spectra grouper here and the label extractor (scripts/extract_val_labels.py) so
    the two can never disagree on what a point is. Precision discs (V4/V5) collapse
    to one disc-level key; everyone else keeps its series; V6/V7 drop out.
    """
    if disc in _NON_VALIDATION_DISCS:
        return None
    if disc in _PRECISION_DISCS:
        return f"JK_V{disc}"            # pool all series -> one point (the 6x mean)
    return f"JK_V{disc}_{series}"       # V1-V3: one point per measurement series


def group_specimens(directory: str | Path) -> dict[str, list[Path]]:
    """Bucket validation OPUS files into the paper's Figure-7 points.

    ``{'JK_V1_1': [JK_V1.1, JK_V1.2, JK_V1.3], 'JK_V4': [all 18 V4 files], ...}``.
    Each file's (disc, series) is parsed from its name and routed through
    ``figure7_key``: V1-V3 split by series, V4/V5 pool every series, V6/V7 dropped.
    Non-matching files (``JK_V2_Test.0``, ``.DS_Store``) are skipped. Keys and paths
    sorted for determinism. The label set (8 points) is what finally selects which of
    these groups become rows -- e.g. V1's third series lands in ``JK_V1_3`` here but
    has no label, so ``assemble_validation_set`` never builds it.
    """
    directory = Path(directory)
    groups: dict[str, list[Path]] = {}
    for path in directory.iterdir():
        m = _VAL_FILE.match(path.name)
        if m is None:
            continue  # not a numeric validation replicate (Test, .DS_Store, ...)
        disc = int(m.group(1))
        series = int(m.group(2)) if m.group(2) else 1   # unnumbered first series = 1
        key = figure7_key(disc, series)
        if key is None:
            continue  # V6 (below cal range) / V7 (optimization sample)
        groups.setdefault(key, []).append(path)

    return {key: sorted(paths) for key, paths in sorted(groups.items())}


def _mean_spectrum(paths: list[Path], ref_axis: np.ndarray) -> np.ndarray:
    """Average a specimen's spectra (all series x all repeats) into one row.

    Self-contained copy of the calibration guard (step 0.4): every file must sit
    on ``ref_axis`` exactly, else averaging would mix two different wavenumbers in
    the same column. We probed all 63 validation spectra onto the cal axis and
    they match bit-for-bit, so this never fires in practice -- but it stays as a
    cheap contract: if a future re-export lands on a different grid, fail loud
    here rather than silently average mismatched channels.
    """
    rows = []
    for p in paths:
        s = load_spectrum(p)
        if not np.array_equal(s.wavenumber, ref_axis):
            raise ValueError(f"{p.name} is on a different wavenumber axis than {ref_axis.size}-pt reference")
        rows.append(s.absorbance)
    # one disc -> one row: collapse every series and repeat into a single mean spectrum
    return np.mean(np.vstack(rows), axis=0)


def assemble_validation_set(spectra_dir: str | Path, labels_csv: str | Path) -> Dataset:
    """Build the 8-point external-validation ``Dataset`` from raw OPUS files + labels.

    The validation twin of ``assemble_dataset`` (0.4): one row per Figure-7 point,
    X/y aligned by key (never by position). Reuses the frozen ``Dataset`` container
    so the validation set is the same shape of object the calibration set is -- the
    2.2 predict step consumes them interchangeably.
    """
    groups = group_specimens(spectra_dir)     # {'JK_V1_1': [3 paths], 'JK_V4': [18], ...}
    labels = read_labels(labels_csv)          # {'JK_V1_1': 47.58, ...} from val_labels.csv

    # The 8 labelled points are the source of truth for which rows exist and their
    # order: we walk sorted(labels), so V1's unlabelled third series (grouped as
    # JK_V1_3) is simply never built. Each label must have a matching spectra group.
    samples = sorted(labels)
    missing = [s for s in samples if s not in groups]
    if missing:
        raise KeyError(f"labelled validation points with no spectra: {missing}")

    # reference axis = first point's first file; every other spectrum is checked against it
    ref_axis = load_spectrum(groups[samples[0]][0]).wavenumber

    # Both comprehensions walk the same `samples` list and fetch by name, so row i of X
    # and element i of y are guaranteed the same point (same discipline as 0.4).
    X = np.vstack([_mean_spectrum(groups[s], ref_axis) for s in samples])
    y = np.array([labels[s] for s in samples])

    assert X.shape == (len(samples), ref_axis.size), f"X shape {X.shape} != ({len(samples)}, {ref_axis.size})"
    assert y.shape == (len(samples),), f"y shape {y.shape} != ({len(samples)},)"
    assert np.isfinite(X).all(), "X contains NaN/inf -- a replicate failed to load cleanly"
    assert np.isfinite(y).all(), "y contains NaN/inf -- a label is missing or non-numeric"

    return Dataset(X=X, y=y, wavenumber=ref_axis, samples=samples)
