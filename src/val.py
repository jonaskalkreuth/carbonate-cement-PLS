"""Assemble the external-validation set: 63 raw replicate files -> one clean (X, y).

Step 2.1. The validation mirror of ``dataset.py`` (step 0.4), but self-contained:
the validation OPUS filenames nest one level deeper and inconsistently
(``specimen _ series . repeat``), so this module carries its own identity rule,
averaging, and axis guard rather than bending the calibration code to fit.

One row per CO2-exposure disc (V1..V6): every series and replicate of a disc is
averaged into a single mean spectrum, matching the paper's Figure 7. The repeated
series are remeasurements of the *same* disc, so counting them as independent
points would be pseudoreplication -- one disc, one row.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from src.dataset import Dataset, read_labels
from src.loader import load_spectrum

# A real validation replicate file is  JK_V<specimen>[_<series>].<repeat>  with all
# numeric fields. Capturing group 1 is the specimen number -> the grouping key.
# The optional (?:_\d+) absorbs the *series* field when present; requiring it to be
# digits is what drops JK_V2_Test.0 (a trial run, no matching label row) for free --
# "_Test" is not "_<digits>", so the pattern simply doesn't match it.
_VAL_FILE = re.compile(r"^JK_V(\d+)(?:_\d+)?\.\d+$")


def group_specimens(directory: str | Path) -> dict[str, list[Path]]:
    """Bucket validation OPUS files by CO2-exposure disc (specimen).

    ``{'JK_V1': [JK_V1.1, JK_V1_2.0, JK_V1_3.0, ...], ...}`` -- all series and
    replicates of one disc collapse under a single ``JK_V<n>`` key. Unlike the
    calibration grouper (which strips a trailing ``.N``), we *grab the prefix*:
    the specimen number is the only stable part of these names, so we match
    ``JK_V<n>`` and ignore whatever series/repeat fields follow. Non-matching
    files (``JK_V2_Test.0``, ``.DS_Store``) are skipped. Keys and paths sorted
    for determinism.
    """
    directory = Path(directory)
    groups: dict[str, list[Path]] = {}
    for path in directory.iterdir():
        m = _VAL_FILE.match(path.name)
        if m is None:
            continue  # not a numeric validation replicate (Test, .DS_Store, ...)
        key = f"JK_V{m.group(1)}"  # group(1) = specimen number, e.g. '4' -> 'JK_V4'
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
    """Build the 6-row external-validation ``Dataset`` from raw OPUS replicates + labels.

    The validation twin of ``assemble_dataset`` (0.4): one row per CO2-exposure
    disc, X/y aligned by specimen key (never by position). Reuses the frozen
    ``Dataset`` container so the validation set is the same shape of object the
    calibration set is -- the 2.2 predict step consumes them interchangeably.
    """
    groups = group_specimens(spectra_dir)     # {'JK_V1': [8 paths], ...}, keys sorted
    labels = read_labels(labels_csv)          # {'JK_V1': 44.72, ...} from val_labels.csv

    # reference axis = first specimen's first file; every other row is checked against it
    first_paths = next(iter(groups.values()))
    ref_axis = load_spectrum(first_paths[0]).wavenumber

    # Align X and y by specimen KEY (same discipline as 0.4): both comprehensions walk
    # the same `samples` list and fetch the label by name, so row i of X and element i
    # of y are guaranteed the same disc. A missing label raises KeyError loudly.
    samples = list(groups)                    # single source of truth for row order
    X = np.vstack([_mean_spectrum(groups[s], ref_axis) for s in samples])
    y = np.array([labels[s] for s in samples])

    assert X.shape == (len(samples), ref_axis.size), f"X shape {X.shape} != ({len(samples)}, {ref_axis.size})"
    assert y.shape == (len(samples),), f"y shape {y.shape} != ({len(samples)},)"
    assert np.isfinite(X).all(), "X contains NaN/inf -- a replicate failed to load cleanly"
    assert np.isfinite(y).all(), "y contains NaN/inf -- a label is missing or non-numeric"

    return Dataset(X=X, y=y, wavenumber=ref_axis, samples=samples)
