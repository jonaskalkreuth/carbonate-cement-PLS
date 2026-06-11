"""Step 1.3 checkpoint: reproduce the paper's Table 3 and judge go/no-go.

Compiles methods a/b/c (src/methods.py), leave-one-out scores each on the
calibration set, and writes an ours-vs-paper comparison to a *committed*
reports/1.3_table3.md -- the durable artifact for the README and interviews.
The pass/fail logic lives in src.methods (testable); this script only renders.

This is the de-risking gate: if the three methods land within tolerance, the
Python reproduction holds and Phase 2 (external validation) is worth building.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so `from src...` works when run as a plain script

from src.dataset import assemble_dataset
from src.methods import (
    METHODS,
    R2_FLOOR_PCT,
    RMSECV_TOL_WTPCT,
    MethodComparison,
    reproduce_all,
)

VERDICT_ICON = {"match": "✅ match", "beats": "🟢 beats paper", "miss": "❌ miss"}

SPECTRA_DIR = ROOT / "data" / "calibration spectra"
LABELS_CSV = ROOT / "data" / "labels.csv"
OUT_MD = ROOT / "reports" / "1.3_table3.md"
MAX_COMPONENTS = 8


def _window_str(intervals: list[tuple[float, float]]) -> str:
    """Render a method's window(s) the way the paper lists them: '683–1620 & …'."""
    return " & ".join(f"{int(lo)}–{int(hi)}" for lo, hi in intervals)


def render_markdown(comparisons: list[MethodComparison]) -> str:
    """Build the ours-vs-paper Table-3 markdown from the scored comparisons."""
    lines = [
        "# Step 1.3 — Table 3 reproduction (go/no-go checkpoint)",
        "",
        "Each method's preprocessing is **selected by an RMSECV search over the "
        "candidates the paper lists** (reproducing OPUS Quant 2's optimize), not "
        "hand-picked. \"Selected\" shows the winner; \"of N\" the candidates searched.",
        "",
        f"Success bar (symmetric): R² ≥ {R2_FLOOR_PCT:.0f}% **and** |ΔRMSECV| ≤ "
        f"{RMSECV_TOL_WTPCT} wt% vs the paper. *beats* = better than the paper by "
        "more than tolerance (best-effort gap, favourable side — does not block GO).",
        "",
        "| Method | Window / cm⁻¹ | Selected (of N) | Factors | R² ours | R² paper | "
        "RMSECV ours | RMSECV paper | ΔRMSECV | CV would pick (dip / 1-SE) | Verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for c in comparisons:
        spec = METHODS[c.name]
        lines.append(
            f"| {c.name} | {_window_str(spec.window)} "
            f"| {c.selection.winner} (of {len(spec.candidates)}) | {c.cv.n_components} "
            f"| {c.r2_pct:.2f} | {c.paper.r2:.2f} "
            f"| {c.cv.rmsecv:.2f} | {c.paper.rmsecv:.2f} "
            f"| {c.rmsecv_delta:+.2f} "
            f"| {c.sweep.best} / {c.sweep.parsimonious} "
            f"| {VERDICT_ICON[c.verdict]} |"
        )

    go = not any(c.blocks_go for c in comparisons)
    beats = [c.name for c in comparisons if c.verdict == "beats"]
    note = "all three reproduce the paper's preprocessing choice within tolerance"
    if go and beats:
        note = (f"every method selects the paper's preprocessing and clears the R² floor; "
                f"method {', '.join(beats)} even beats the paper (best-effort gap)")
    elif not go:
        note = "at least one method is worse than the paper beyond tolerance — investigate before proceeding"
    lines += ["", f"**Checkpoint: {'GO' if go else 'NO-GO'}** — {note}."]
    return "\n".join(lines) + "\n"


def main() -> None:
    ds = assemble_dataset(SPECTRA_DIR, LABELS_CSV)
    comparisons = reproduce_all(ds.X, ds.y, ds.wavenumber, max_components=MAX_COMPONENTS)

    # Console echo so a run is legible without opening the file.
    for c in comparisons:
        print(f"method {c.name}: selected {c.selection.winner} of {len(METHODS[c.name].candidates)}, "
              f"R²={c.r2_pct:.2f}% (paper {c.paper.r2}), "
              f"RMSECV={c.cv.rmsecv:.2f} wt% (paper {c.paper.rmsecv}, Δ{c.rmsecv_delta:+.2f}), "
              f"factors={c.cv.n_components}, CV-pick dip/1-SE={c.sweep.best}/{c.sweep.parsimonious}, "
              f"{c.verdict.upper()}")

    OUT_MD.parent.mkdir(exist_ok=True)
    OUT_MD.write_text(render_markdown(comparisons), encoding="utf-8")
    print(f"\nwrote table -> {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
