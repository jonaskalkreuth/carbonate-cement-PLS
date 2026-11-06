# carbonate-cement-PLS — Project Spec (shared understanding)

> **Status (2026-11-06):** planning doc from 2026-06-10. It states goals, not results; the paper is not yet reproduced. Current status is in `README.md`.
>
> Output of a `/grill-me` session on 2026-06-10. Captures the decisions that
> shape the project, before decomposition (`/design-tree`) and build.
> Portfolio project **2 of 3** (see `../plan.md`). Sibling project:
> `../ir-spectra-analyzer` (FTIR *classification*) — this is the *regression* piece.

## One-line pitch (draft)
Reproduce a peer-reviewed ATR-IR + PLS method for quantifying CaCO₃ in carbonated
cement paste — in open-source Python instead of Bruker's commercial OPUS Quant2 —
hit the same published accuracy, then show *why* the multivariate model is needed.

## Source of truth
Kalkreuth et al., *J. Am. Ceram. Soc.* 2023, DOI 10.1111/jace.19546 (open access,
**user is first author**). "Accelerated carbonation of hardened cement paste:
Quantification of calcium carbonate via ATR infrared spectroscopy."

## The task
- **X:** ATR-IR absorbance spectra (`'a'` block of Bruker OPUS binary files).
- **y:** CaCO₃ wt% per sample, from TG-FTIR (the paper's reference method) — taken
  as given (consumed, not re-derived) from the lab Excel.
- **Model:** PLS regression (the paper used OPUS "Quant 2"; we use Python/sklearn).
- **Target to reproduce:** Table 3 — 3 methods, R² 99.47–99.62%, RMSECV 1.1–1.38 wt%,
  3–4 factors, each with specific preprocessing combos + spectral windows.

## Data inventory (in `data/`, local)
- `calibration spectra/` — OPUS files for JK_MV_01…12 (11–12 samples, multiple
  replicate files each, e.g. `.0/.1/.2`).
- `validation spectra/` — OPUS files for JK_V1…V6 (CO₂-exposure-time specimens;
  V4/V5 measured ~6× for precision).
- Excel (local only, **not** published): `Auswertung TG-FTIR-ATR-Kalibrierung.xlsx`
  (per-sample TG-FTIR CaCO₃ wt%, the labels), `Zusammenfassung aller Experimente…xlsx`
  (TG/XRF/XRD/all samples), `Berechnung CO2-Uptake.xlsx`.
- OPUS parsing confirmed working via the `brukeropus` library (`'a'` = absorbance,
  ~400–4000 cm⁻¹, ~5049 points).

## Decisions (locked)

| # | Decision | Choice |
|---|----------|--------|
| 1 | y-data | Exists: TG-FTIR CaCO₃ wt% per sample, from Excel. Real supervised regression. |
| 2 | Narrative | **Reproduce-in-Python, then extend.** Spine = faithfully reproduce the published OPUS result; then honest extensions. Same ethos as project 1. |
| 3 | Validation data | Have both calibration **and** validation OPUS spectra → full reproduction (Table 3 + Figure 7) feasible. |
| 4 | Data assembly | **Average each sample's replicate spectra → one row (n≈11)**, matching the paper, leave-one-out CV. Replicates with **group-aware CV** as a bonus leakage demo. |
| 5 | Preprocessing fidelity | **Match the result, not the bits.** Standard steps (SNV/MSC/Savitzky-Golay deriv) exact; OPUS-specific steps (SLS/LOS/MMN) best-effort. Reproduced = land Table 3 metrics within tolerance; bit-exact match to closed algorithm NOT claimed. |
| 6 | Extensions | **All four:** (a) univariate band-area baseline as the *motivating floor* (expected to fail because carbonate band shape depends on the modification mix — calcite/aragonite/vaterite/ACC/monocarbonate — not just concentration → motivates PLS); (b) **interpretability** — PLS coefficients/VIP peak at carbonate bands (712, 873, 1300–1600 cm⁻¹), dip at Ca(OH)₂/C-S-H — *headline*; (c) light, honest preprocessing/window search w/ small-n caveat; (d) brief PLS-vs-PCR/Ridge note. |
| 7 | Deliverable | **Match project 1:** `src/` package (OPUS loader, preprocessing, PLS, baseline, interpretation), `scripts/` to regenerate figures/tables, narrative notebook, README w/ results-vs-paper table, pytest suite, "predict CaCO₃ from a new spectrum" CLI capstone. Early "do the numbers reproduce?" checkpoint before full scaffolding. |
| 8 | Success bar | **All 3 methods**, success = R² ≥ ~99% and RMSECV within ~±0.3 wt% of paper, same 3–4 factor count. Report side-by-side with the paper. |
| 9 | Reproduction depth | **Stages 1 + 2 core** (calibration/CV = Table 3; external validation on V-samples = Figure 7). Stage 3 (optimize-by-augmentation, Table 5) optional + critiqued. |
| 10 | Data publishing | **Minimal subset only.** Publish spectra + a small derived `labels` file (sample → CaCO₃ wt% TG-FTIR). Keep multi-experiment Excel (TG/XRF/XRD) OUT of public repo (gitignored, used locally to build labels). Cite the open-access paper. |
| 11 | Scope | **ATR-IR → PLS → CaCO₃ wt% only.** Excluded (cited, not reproduced): TG/TG-FTIR method dev, XRF/RFA, XRD, CO₂-uptake kinetics, synthetic-phase assignment. TG-FTIR values consumed as labels. |

## Honest limitations to foreground (README/notebook)
- **n ≈ 11** — tiny; cross-validation can be optimistic, so external validation matters.
- Univariate band-area is expected to be biased — band shape encodes carbonate
  *speciation*, not just total concentration.
- Paper's own caveats: ATR result depends on C/S ratio, particle size, cement type;
  **external validation** spanned ~20–48 wt% CaCO₃. _Note (confirmed against the
  thesis): the 20–48 wt% range is the validation window only — the PLS calibration
  was fit on all 12 JK_MV samples (2.45–61.26 wt%). So the full calibration span in
  `labels.csv` is correct and expected, not a divergence to re-check at 1.3._

## Open items for /design-tree and build
- Map each OPUS sample → its TG-FTIR CaCO₃ label (parse `Auswertung…xlsx`).
- Confirm which/how many calibration samples (11 vs 12 incl. cross-val sample).
- Decide exact `.dpt`/OPUS replicate handling & which OPUS block (`'a'`).
- Repo init: git, `.gitignore` (Excel + raw OPUS dumps as decided), license, requirements.
- Reproduce the exact spectral windows + preprocessing combos of methods a/b/c.
