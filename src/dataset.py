"""Assemble the modelling dataset: 36 raw replicate files -> one clean (X, y).

Step 0.4. Bridges the loader (step 0.2) and labels (step 0.3) into the single
``Dataset`` object the PLS harness (step 1.2) consumes. One row per sample:
replicates averaged, all spectra asserted onto a shared wavenumber axis, X rows
aligned to y by sample key (never by position).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from src.loader import group_replicates, load_spectrum


@dataclass(frozen=True)
class Dataset:
    """The calibration set as aligned arrays plus the axis and sample order.

    Frozen, like ``Spectrum``: the assembled data is a fixed snapshot. Row ``i``
    of ``X``, element ``i`` of ``y``, and ``samples[i]`` always refer to the same
    sample — ``samples`` is the single source of truth for row order.
    """

    X: np.ndarray           # (n_samples, n_channels) mean absorbance per sample
    y: np.ndarray           # (n_samples,) CaCO3 wt%, aligned row-for-row to X
    wavenumber: np.ndarray  # (n_channels,) shared axis, ascending
    samples: list[str]      # (n_samples,) sample keys, aligned to X rows / y


def read_labels(labels_csv: str | Path) -> dict[str, float]:
    """Read ``labels.csv`` (step 0.3) into ``{'JK_MV_01': 2.45, ...}``."""
    labels_csv = Path(labels_csv)
    with labels_csv.open(newline="") as f:
        reader = csv.DictReader(f)
        return {row["sample"]: float(row["caco3_wt_pct"]) for row in reader}


def _mean_spectrum(paths: list[Path], ref_axis: np.ndarray) -> np.ndarray:
    """Average a sample's replicate absorbance vectors into one row.

    B1 guard: every replicate must sit on ``ref_axis`` exactly (we verified all
    cal spectra share one 5049-pt axis). A mismatch means slot ``i`` would mix
    two different wavenumbers when averaged, so we fail loud instead.
    """
    rows = []
    for p in paths:
        s = load_spectrum(p)
        if not np.array_equal(s.wavenumber, ref_axis):
            raise ValueError(f"{p.name} is on a different wavenumber axis than {ref_axis.size}-pt reference")
        rows.append(s.absorbance)
    # mean over replicates: stack to (n_replicates, n_channels), average down the rows
    return np.mean(np.vstack(rows), axis=0)


def assemble_dataset(spectra_dir: str | Path, labels_csv: str | Path) -> Dataset:
    """Build the calibration ``Dataset`` from raw OPUS replicates + labels.csv.

    Averages each sample's replicates, asserts a shared wavenumber axis (B1),
    and aligns X/y by sample key. ``samples`` (sorted loader keys) is the single
    source of truth for row order.
    """
    groups = group_replicates(spectra_dir)   # {'JK_MV_01': [3 paths], ...}, keys sorted
    labels = read_labels(labels_csv)

    # reference axis = the first replicate's axis; every other row is checked against it
    first_paths = next(iter(groups.values()))
    ref_axis = load_spectrum(first_paths[0]).wavenumber

    # Align X and y by sample KEY, not by position. Both comprehensions iterate the
    # same `samples` list and fetch each sample's label by name (labels[s]) -- so row i
    # of X and element i of y are guaranteed to be the same sample, whatever order the
    # CSV or loader happened to use. Position-zipping two lists would misalign silently
    # if their orders ever diverged; here a missing label raises KeyError loudly instead.
    samples = list(groups)                    # single source of truth for row order
    X = np.vstack([_mean_spectrum(groups[s], ref_axis) for s in samples])
    y = np.array([labels[s] for s in samples])

    # Structural invariants: cheap contract that catches a malformed build immediately,
    # before any of it reaches PLS. Each row of X must pair with one y and one axis point.
    assert X.shape == (len(samples), ref_axis.size), f"X shape {X.shape} != ({len(samples)}, {ref_axis.size})"
    assert y.shape == (len(samples),), f"y shape {y.shape} != ({len(samples)},)"
    assert np.isfinite(X).all(), "X contains NaN/inf -- a replicate failed to load cleanly"
    assert np.isfinite(y).all(), "y contains NaN/inf -- a label is missing or non-numeric"

    return Dataset(X=X, y=y, wavenumber=ref_axis, samples=samples)
