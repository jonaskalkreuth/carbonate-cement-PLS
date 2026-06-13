"""Step 2.2: reproduce the paper's Figure 7 + the external-validation numbers.

Fits methods a/b/c on the full calibration set, predicts the 6 held-out V-discs,
and renders (1) the two-panel Figure 7 -- predicted-vs-reference and per-disc
relative error -- as a PNG, and (2) a committed reports/2.2_figure7.md with RMSEP,
R²_ext, bias, the paired t-test p-value, and the headline cal->val gap.

Unlike 1.3 this is descriptive, not a go/no-go: the point is to *show* how much
error the honest external test adds over the optimistic cal CV. The metric logic
lives in src.validate (testable); this script only runs it and renders.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so `from src...` works when run as a plain script

import matplotlib.pyplot as plt

from src.dataset import assemble_dataset
from src.val import assemble_validation_set
from src.validate import ValidationResult, validate_all

CAL_SPECTRA = ROOT / "data" / "calibration spectra"
CAL_LABELS = ROOT / "data" / "labels.csv"
VAL_SPECTRA = ROOT / "data" / "validation spectra"
VAL_LABELS = ROOT / "data" / "val_labels.csv"
OUT_PNG = ROOT / "reports" / "2.2_figure7.png"
OUT_MD = ROOT / "reports" / "2.2_figure7.md"

# One colour/marker per method so both panels read as the same three series.
STYLE = {"a": ("tab:blue", "o"), "b": ("tab:orange", "s"), "c": ("tab:green", "^")}


def plot_figure7(results: list[ValidationResult]) -> plt.Figure:
    """Two-panel Figure 7: predicted-vs-reference (left), relative error (right).

    Both panels share the reference CaCO3 on the x-axis, so a disc that the model
    over-predicts sits above the 1:1 line on the left *and* above zero on the right.
    The 1:1 line is the "perfect prediction" locus -- points below it are
    under-estimates, above are over-estimates (the paper's central finding).
    """
    fig, (ax_pred, ax_rel) = plt.subplots(1, 2, figsize=(12, 5))

    # --- Left: predicted vs reference, with the 1:1 line ---
    # Span the line across the full data range of BOTH axes so it frames every point.
    lo = min(min(r.y_true.min(), r.y_pred.min()) for r in results)
    hi = max(max(r.y_true.max(), r.y_pred.max()) for r in results)
    ax_pred.plot([lo, hi], [lo, hi], "k--", lw=1, label="1:1 (perfect)")
    for r in results:
        colour, marker = STYLE[r.name]
        ax_pred.scatter(r.y_true, r.y_pred, c=colour, marker=marker, s=60,
                        label=f"method {r.name} ({r.winner})")
    ax_pred.set_xlabel("TG-FTIR reference CaCO₃ / wt%")
    ax_pred.set_ylabel("predicted CaCO₃ / wt%")
    ax_pred.set_title("Predicted vs reference (external V-discs)")
    ax_pred.set_aspect("equal", adjustable="box")  # 1:1 line must look 1:1
    ax_pred.legend(fontsize=8)

    # --- Right: relative error vs reference ---
    ax_rel.axhline(0, color="k", lw=1)               # zero-error reference
    for band in (8, -8):                              # paper's ~8-9% envelope for a & c
        ax_rel.axhline(band, color="0.7", ls=":", lw=1)
    for r in results:
        colour, marker = STYLE[r.name]
        ax_rel.scatter(r.y_true, r.relative_error, c=colour, marker=marker, s=60,
                       label=f"method {r.name}")
    ax_rel.set_xlabel("TG-FTIR reference CaCO₃ / wt%")
    ax_rel.set_ylabel("relative error / %")
    ax_rel.set_title("Relative error vs reference")
    ax_rel.legend(fontsize=8)

    fig.suptitle("Figure 7 reproduction — external validation on held-out V-discs (step 2.2)")
    fig.tight_layout()
    return fig


# Paper's paired t-test p-values (predicted vs reference), the one hard Figure-7 number.
PAPER_PVALUE = {"a": 0.526, "b": 0.241, "c": 0.730}


def render_markdown(results: list[ValidationResult]) -> str:
    """Build the committed external-validation report from the scored results."""
    lines = [
        "# Step 2.2 — Figure 7 reproduction (external validation)",
        "",
        "Each method is fit on **all 12 calibration discs** (winning preprocessing "
        "re-derived by the same search as 1.3) and predicts the paper's **8 Figure-7 "
        "points** (V1–V3 measured in two series each → 6 points; V4 & V5, the precision "
        "discs at 48 & 20 wt%, each the mean of 6 series; V6 below the calibration range "
        "and V7 the optimization sample are excluded). Unlike 1.3 this is descriptive, "
        "not a gate: the headline is the **cal→val gap** (RMSEP − RMSECV) — how much "
        "error the honest external test adds over the optimistic in-sample CV.",
        "",
        "| Method | Winner | RMSECV (cal) | RMSEP (val) | gap | R²_ext | bias | p (ours) | p (paper) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r.name} | {r.winner} | {r.rmsecv_cal:.2f} | {r.rmsep:.2f} "
            f"| {r.gap:+.2f} | {r.r2_ext:.3f} | {r.bias:+.2f} "
            f"| {r.p_value:.3f} | {PAPER_PVALUE[r.name]:.3f} |"
        )

    # The t-test conclusion is the reproducible target: all p > 0.05 => no significant
    # difference from the reference, matching the paper regardless of the exact p.
    all_ns = all(r.p_value > 0.05 for r in results)
    worst = max(results, key=lambda r: r.gap)
    lines += [
        "",
        f"RMSECV (cal) is in wt%; RMSEP (val) in wt%; bias = mean(pred − ref), "
        f"+ve = systematic over-estimate. Relative-error envelope and the trend "
        f"(under mid-range, over above ~47 wt%) are in `2.2_figure7.png`.",
        "",
        f"**External validation: the gap is the point.** RMSEP runs "
        f"{min(r.rmsep for r in results):.1f}–{max(r.rmsep for r in results):.1f} wt% "
        f"versus RMSECV {min(r.rmsecv_cal for r in results):.1f}–"
        f"{max(r.rmsecv_cal for r in results):.1f} wt% — a {worst.gap:+.1f} wt% jump at "
        f"worst (method {worst.name}), the optimism of in-sample CV at n≈11 made visible. "
        + ("All three paired t-tests give p > 0.05 → **no significant difference from the "
           "TG-FTIR reference**, reproducing the paper's conclusion (exact p differs: "
           "best-effort preprocessing gap)." if all_ns else
           "At least one paired t-test gives p ≤ 0.05 → a significant difference from the "
           "reference, unlike the paper — investigate."),
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    cal = assemble_dataset(CAL_SPECTRA, CAL_LABELS)
    val = assemble_validation_set(VAL_SPECTRA, VAL_LABELS)
    results = validate_all(cal, val)

    # Console echo so a run is legible without opening the artifacts.
    for r in results:
        print(f"method {r.name}: {r.winner}  RMSECV={r.rmsecv_cal:.2f} -> RMSEP={r.rmsep:.2f} "
              f"(gap {r.gap:+.2f}), R²_ext={r.r2_ext:.3f}, bias={r.bias:+.2f}, "
              f"p={r.p_value:.3f} (paper {PAPER_PVALUE[r.name]})")

    OUT_PNG.parent.mkdir(exist_ok=True)
    fig = plot_figure7(results)
    fig.savefig(OUT_PNG, dpi=120)
    OUT_MD.write_text(render_markdown(results), encoding="utf-8")
    print(f"\nsaved plot  -> {OUT_PNG.relative_to(ROOT)}")
    print(f"wrote report -> {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
