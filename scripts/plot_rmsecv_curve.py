"""Step 1.2 diagnostic: draw the RMSECV-vs-#factors curve for a demo recipe.

Runs the LOOCV harness across factor counts on a simple crop+SNV+PLS pipeline and
plots the U-shaped error curve, marking the lowest dip and the one-standard-error
"safe choice". This is a harness check, not a result -- the paper's exact recipes
and pinned factor counts arrive in step 1.3; this just proves the curve renders
and the sweet spot is where chemometric intuition expects it (a few factors).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so `from src...` works when run as a plain script

import matplotlib.pyplot as plt
from sklearn.cross_decomposition import PLSRegression
from sklearn.pipeline import Pipeline

from src.dataset import assemble_dataset
from src.pls import sweep_factors
from src.preprocessing import StandardNormalVariate, WavenumberWindow

SPECTRA_DIR = ROOT / "data" / "calibration spectra"
LABELS_CSV = ROOT / "data" / "labels.csv"
OUT_PNG = ROOT / "reports" / "1.2_rmsecv_curve.png"
MAX_COMPONENTS = 8


def main() -> None:
    ds = assemble_dataset(SPECTRA_DIR, LABELS_CSV)

    # Demo recipe only: crop the ATR edge + a broad fingerprint window, SNV, PLS.
    # n_components here is a placeholder -- sweep_factors overrides it 1..MAX.
    pipe = Pipeline([
        ("crop", WavenumberWindow(ds.wavenumber, [(500, 1800)])),
        ("snv", StandardNormalVariate()),
        ("pls", PLSRegression(n_components=1)),
    ])

    sweep = sweep_factors(pipe, ds.X, ds.y, max_components=MAX_COMPONENTS)
    print(f"RMSECV by factor: {[round(v, 3) for v in sweep.rmsecv.tolist()]}")
    print(f"lowest dip: {sweep.best} factors   one-SE safe choice: {sweep.parsimonious} factors")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(sweep.n_components, sweep.rmsecv, "o-", color="0.3", lw=1.5, label="RMSECV")
    # Mark the two suggested factor counts so the U-shape's sweet spot is obvious.
    ax.axvline(sweep.best, color="tab:blue", ls="--", lw=1,
               label=f"lowest dip ({sweep.best})")
    ax.axvline(sweep.parsimonious, color="tab:green", ls=":", lw=1.5,
               label=f"one-SE safe choice ({sweep.parsimonious})")
    ax.set_xlabel("number of PLS factors")
    ax.set_ylabel("RMSECV / wt%")
    ax.set_title("LOOCV error vs PLS factor count (demo recipe, step 1.2)")
    ax.legend()

    OUT_PNG.parent.mkdir(exist_ok=True)
    fig.tight_layout()
    fig.savefig(OUT_PNG, dpi=120)
    print(f"saved curve -> {OUT_PNG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
