"""Load Bruker OPUS ATR-IR spectra and group replicate measurements per sample.

Step 0.2: read one OPUS file -> Spectrum (absorbance 'a' block, ascending
wavenumber), and bucket replicate files (``JK_MV_01.0/.1/.2``) by sample.
Averaging and common-grid resampling are deliberately left to step 0.4.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from brukeropus import read_opus


@dataclass(frozen=True)
class Spectrum:
    """One ATR-IR measurement: two aligned vectors plus where it came from.

    Frozen so measured data is read-only — preprocessing produces *new*
    arrays rather than mutating the original measurement.
    """

    wavenumber: np.ndarray  # cm^-1, ascending (~400 -> ~3998)
    absorbance: np.ndarray  # OPUS 'a' block, aligned element-wise to wavenumber
    source: Path            # provenance: which file this came from


def load_spectrum(path: str | Path) -> Spectrum:
    """Read one Bruker OPUS file into a Spectrum (absorbance 'a' block).

    Wavenumber is returned ascending (OPUS stores it descending), so every
    downstream array shares one orientation.
    """
    path = Path(path)
    opus = read_opus(path)

    x = np.asarray(opus.a.x, dtype=float)  # native OPUS order: descending
    y = np.asarray(opus.a.y, dtype=float)

    order = np.argsort(x)  # sort-by-wavenumber, not [::-1]: correct even if not strictly monotonic
    return Spectrum(wavenumber=x[order], absorbance=y[order], source=path)


_REPLICATE_SUFFIX = re.compile(r"\.\d+$")  # trailing dot-then-digits, e.g. ".0", ".12"


def _sample_key(path: Path) -> str:
    """Sample root for a replicate file: 'JK_MV_01.2' -> 'JK_MV_01'."""
    return _REPLICATE_SUFFIX.sub("", path.name)


def group_replicates(directory: str | Path) -> dict[str, list[Path]]:
    """Bucket OPUS replicate files in *directory* by sample.

    ``{'JK_MV_01': [JK_MV_01.0, JK_MV_01.1, JK_MV_01.2], ...}``. The key is only
    the bucket label; each file keeps its full path in the list. Replicate files
    are matched by a trailing ``.N`` suffix, so non-spectra (``.DS_Store``,
    ``labels.csv``) are skipped. Paths within a group are sorted for determinism.
    """
    directory = Path(directory)
    groups: dict[str, list[Path]] = {}
    for path in directory.iterdir():
        if not _REPLICATE_SUFFIX.search(path.name):
            continue  # not a replicate file (.DS_Store, stray .csv, etc.)
        groups.setdefault(_sample_key(path), []).append(path)

    return {key: sorted(paths) for key, paths in sorted(groups.items())}
