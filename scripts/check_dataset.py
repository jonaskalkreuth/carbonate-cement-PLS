"""Step 0.4 sanity check: assemble the calibration dataset and eyeball it.

Prints the shapes + label range, then overlays the 12 mean spectra coloured by
CaCO3 wt% -- if the assembly is sound, the carbonate bands should deepen with
concentration. Saves the figure to reports/ rather than blocking on a window.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so `from src...` works when run as a plain script

import matplotlib.pyplot as plt
import numpy as np

from src.dataset import assemble_dataset

SPECTRA_DIR = ROOT / "data" / "calibration spectra"
LABELS_CSV = ROOT / "data" / "labels.csv"
OUT_PNG = ROOT / "reports" / "0.4_calibration_overlay.png"


def main() -> None:
    ds = assemble_dataset(SPECTRA_DIR, LABELS_CSV)

    print(f"X: {ds.X.shape}  y: {ds.y.shape}  axis: {ds.wavenumber.size} pts")
    print(f"wavenumber: {ds.wavenumber.min():.1f} -> {ds.wavenumber.max():.1f} cm-1")
    print(f"CaCO3 label range: {ds.y.min():.2f} -> {ds.y.max():.2f} wt%  (n={len(ds.samples)})")

    # Colour each sample's mean spectrum by its CaCO3 wt%: a visual alignment check.
    # If X and y are correctly paired, higher-CaCO3 samples should show stronger
    # carbonate absorption -- a wrong pairing would scramble that gradient.
    norm = plt.Normalize(ds.y.min(), ds.y.max())
    cmap = plt.cm.viridis

    fig, ax = plt.subplots(figsize=(10, 6))
    for row, conc in zip(ds.X, ds.y):
        ax.plot(ds.wavenumber, row, color=cmap(norm(conc)), lw=0.8, alpha=0.9)
    ax.set_xlabel("wavenumber / cm$^{-1}$")
    ax.set_ylabel("absorbance")
    ax.set_title("Calibration mean spectra, coloured by CaCO$_3$ wt% (step 0.4)")
    ax.invert_xaxis()  # spectroscopy convention: high wavenumber on the left
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, label="CaCO$_3$ wt%")

    OUT_PNG.parent.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=120)
    print(f"saved overlay -> {OUT_PNG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
