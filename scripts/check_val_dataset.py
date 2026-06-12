"""Step 2.1 sanity check: assemble the external-validation set and eyeball it.

The validation twin of ``check_dataset.py`` (0.4). Prints shapes + label range,
then overlays the 6 mean validation spectra coloured by CaCO3 wt% -- if the
assembly is sound, carbonate bands should deepen with concentration, same as
calibration. Saves to reports/ rather than blocking on a window.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so `from src...` works when run as a plain script

import matplotlib.pyplot as plt

from src.val import assemble_validation_set

SPECTRA_DIR = ROOT / "data" / "validation spectra"
LABELS_CSV = ROOT / "data" / "val_labels.csv"
OUT_PNG = ROOT / "reports" / "2.1_validation_overlay.png"

# The paper's external-validation window (thesis): V1-V5 land inside, V6 sits below.
PAPER_WINDOW = (20.0, 48.0)


def main() -> None:
    ds = assemble_validation_set(SPECTRA_DIR, LABELS_CSV)

    print(f"X: {ds.X.shape}  y: {ds.y.shape}  axis: {ds.wavenumber.size} pts")
    print(f"wavenumber: {ds.wavenumber.min():.1f} -> {ds.wavenumber.max():.1f} cm-1")
    print(f"CaCO3 label range: {ds.y.min():.2f} -> {ds.y.max():.2f} wt%  (n={len(ds.samples)})")
    lo, hi = PAPER_WINDOW
    for s, v in zip(ds.samples, ds.y):
        flag = "" if lo <= v <= hi else "  <- outside paper's 20-48 wt% window"
        print(f"  {s}: {v:6.2f} wt%{flag}")

    # Same alignment check as 0.4: colour each disc's mean spectrum by its CaCO3 wt%.
    # Correct X/y pairing => carbonate bands deepen monotonically with the colour scale.
    norm = plt.Normalize(ds.y.min(), ds.y.max())
    cmap = plt.cm.viridis

    fig, ax = plt.subplots(figsize=(10, 6))
    for row, conc in zip(ds.X, ds.y):
        ax.plot(ds.wavenumber, row, color=cmap(norm(conc)), lw=0.8, alpha=0.9)
    ax.set_xlabel("wavenumber / cm$^{-1}$")
    ax.set_ylabel("absorbance")
    ax.set_title("Validation mean spectra, coloured by CaCO$_3$ wt% (step 2.1)")
    ax.invert_xaxis()  # spectroscopy convention: high wavenumber on the left
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, label="CaCO$_3$ wt%")

    OUT_PNG.parent.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=120)
    print(f"saved overlay -> {OUT_PNG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
