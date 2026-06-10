# Design tree: carbonate-cement-PLS

> Companion to `SPEC.md` (the `/grill-me` shared-understanding doc). This is the
> decomposition into individually-workable pieces. Portfolio project 2 of 3.

## Key decisions
- **Narrative** → Reproduce the published OPUS Quant2 ATR-IR+PLS method in open-source Python, then extend. _Why: proves you can replicate a peer-reviewed commercial-software result in code; same honest-validation voice as project 1._
- **Top-level tree axis** → By pipeline phase, reproduction-first. _Why: front-loads the "do the numbers reproduce?" risk before investing in full package scaffolding; mirrors the real build order._
- **Data assembly** → Average replicates → one row per sample (n≈11), LOOCV; replicates + group-aware CV as a bonus. _Why: matches the paper for an apples-to-apples Table 3 comparison._
- **Preprocessing fidelity** → Match the result within tolerance, not bit-exact. _Why: OPUS SLS/LOS/MMN algorithms are closed; bit-exact match is infeasible and low-value._
- **Extensions** → All four; univariate baseline as the *motivating floor*, interpretability as headline. _Why: depth over breadth, all chemically defensible._
- **Deliverable** → Match project 1 (package + scripts + notebook + tests + CLI + README). _Why: coherent portfolio voice._
- **Data publishing** → Minimal subset only (spectra + derived labels); Excel gitignored. _Why: supervisor cleared *use*, not publishing the full multi-experiment lab data._
- **Scope** → ATR-IR → PLS → CaCO₃ wt% only; everything else cited, not reproduced.

## Tree
- **carbonate-cement-PLS** (reproduce ATR-IR+PLS CaCO₃ quantification in Python, then extend)
  - **Phase 0 — Foundation**
    - [x] **0.1 Repo scaffolding & data staging** — git init, dir skeleton, requirements, LICENSE, stub README, .gitignore (Excel + regenerable artifacts), commit minimal data subset (calibration + validation OPUS spectra). _why leaf: execution only, publishing decision already made._  ✅ commit `e8379af`: 112 files, 99 OPUS spectra staged, Excel + .DS_Store gitignored before first commit; MIT + CC-BY-4.0 dual license.
    - [ ] **0.2 OPUS loader** (`src`) — parse OPUS binary → (wavenumber, absorbance) from `'a'` block; discover + group replicate files per sample. _why leaf: block + grouping decided, just implement._
    - [ ] **0.3 Label extraction → committed `labels.csv`** — parse `Auswertung…xlsx`, map sample → TG-FTIR CaCO₃ wt%, write the one published derived file. _why leaf: source + target decided._  (verify sample names match spectra filenames)
    - [ ] **0.4 Assemble modelling dataset** — average replicates per sample, resample to common wavenumber grid, align X with y, sanity check (overlay plot + label range). _why leaf: average + common-grid decided._  (needs 0.2 + 0.3 first)
  - **Phase 1 — Reproduce core** *(the de-risking checkpoint)*
    - [ ] **1.1 Preprocessing toolkit** (`src`) — composable transforms: SNV, MSC, Savitzky-Golay 1st-deriv (exact) + OPUS best-effort SLS/LOS/MMN + spectral-window cropping. _why leaf: "match result not bits" decided; just implement._
    - [ ] **1.2 PLS + LOOCV harness** (`src`) — sklearn PLSRegression, leave-one-out CV, R²/RMSECV, RMSECV-vs-#factors curve. _why leaf: model + CV scheme decided._
    - [ ] **1.3 Reproduce methods a/b/c → Table 3 + checkpoint** — wire each method's exact preprocessing combo + spectral window(s) + factor count; results-vs-paper table; **go/no-go: within tolerance?** _why leaf: configs given by Table 3, execution._  (needs 1.1, 1.2, Phase 0)
  - **Phase 2 — External validation**
    - [ ] **2.1 Build validation set** — load V-sample OPUS spectra, average replicates, grid-align, join to TG-FTIR labels. _why leaf: mirrors 0.4 on the validation dataset._  (needs 0.2, 0.3, 0.4; 0.3 extracts cal+val labels)
    - [ ] **2.2 Predict + reproduce Figure 7** — fit each method on calibration, predict on V-samples, predicted-vs-reference + relative-error plots vs paper. _why leaf: execution, all 3 methods._  (needs 1.3, 2.1)
    - [ ] **2.3 _(optional)_ Stage-3 optimize-by-augmentation + critique** — fold 8 V-samples into calibration, re-validate on remaining 3 (Table 5), critique mixing val into cal. _why leaf: clearly-scoped stretch._  (needs 2.2)
  - **Phase 3 — Extensions**
    - [ ] **3.1 Univariate band-area baseline (motivating floor)** — integrate a carbonate band, straight-line calibration, LOOCV; show underperformance + bias, write chemical "why it fails" (speciation). _why leaf: method decided._  (needs Phase 0, 1.2)
    - [ ] **3.2 Interpretability — coefficients hit the chemistry _(headline)_** — PLS coeff/VIP on wavenumber axis, annotate carbonate vs Ca(OH)₂/C-S-H bands. _why leaf: execution._  (needs 1.3)
    - [ ] **3.3 Replicate-level group-aware CV (leakage demo)** — raw replicates; naive-split (leaky) vs group-aware (honest) gap. _why leaf: signature move, execution._  (needs Phase 0 loader, 1.2)
    - [ ] **3.4 Preprocessing/window search (light, honest)** — grid over combos+windows w/ group-aware CV, report grid + small-n caveat. _why leaf: execution._  (reuses 3.3; needs 1.1, 1.2)
    - [ ] **3.5 PLS vs PCR/Ridge (brief note)** — same CV, report differences within noise at n≈11. _why leaf: deliberately small._  (needs 1.2)
  - **Phase 4 — Package & polish**
    - [ ] **4.1 Consolidate `src/` package** — refactor phases 1–3 code into coherent modules (loader, preprocessing, pls, baseline, interpret, config) + docstrings/clean API. _why leaf: cleanup pass, execution._  (needs Phase 1–3 code)
    - [ ] **4.2 Reproduction scripts → `reports/`** — scripts regenerating Table 3, Figure 7, interpretation + baseline plots into committed reports/. _why leaf: execution._  (needs 1.3, 2.2, 3.x)
    - [ ] **4.3 CLI capstone** — predict CaCO₃ wt% + uncertainty from a new spectrum; persist trained model. _why leaf: execution._  (needs 4.1, 1.3)
    - [ ] **4.4 pytest suite** — loader, each preprocessing transform, PLS harness, label extraction; synthetic fixtures so it runs without raw data. _why leaf: execution._  (needs 4.1)
    - [ ] **4.5 Narrative notebook** — reproduce-then-extend story end-to-end. _why leaf: writeup, execution._  (needs 1.3, 2.2, 3.x)
    - [ ] **4.6 README** — pitch, results-vs-paper table, methodology + honest caveats (n≈11, speciation, ATR limits), install/usage/reproduce, data & license + paper citation. _why leaf: writeup._  (needs results + 4.2)

## Implementation decisions (per-step, from /learn-while-building)
- **0.1 — layout (B2):** `src/` layout with **flat modules + `src/__init__.py`**, mirroring sibling `ir-spectra-analyzer` (no nested package dir, no installable package; scripts import via a `sys.path` shim → `from src.loader import …`).
- **0.1 — dependencies (C1):** plain `requirements.txt` with `>=` ranges (project-1 style). Deps: numpy, pandas, scipy, matplotlib, scikit-learn, joblib + `brukeropus` (OPUS binary parsing) + `openpyxl` (read label Excel).
- **0.1 — license (D3):** MIT for code, **CC-BY-4.0** for the committed spectra (data ≠ software; cite the JACE paper). _Note: project 1 ships no license; this is an intentional improvement, not a divergence._
- **0.1 — data staging:** commit all 35 calibration + 63 validation OPUS files (~9 MB, flat binary files named `JK_*.N` where `.N` = replicate). Gitignore the 3 Excel files + `.DS_Store` + artifacts **before** the first commit.
- **0.1 — dirs:** `src/ tests/ scripts/ notebooks/ reports/ models/ data/` (matches project 1).

## Next up
> Ordered for reproduction-first build; reorder freely. The **checkpoint at #7** is the go/no-go — don't invest in packaging until the numbers reproduce.

1. [x] **0.1** Repo scaffolding & data staging
2. [ ] **0.2** OPUS loader
3. [ ] **0.3** Label extraction → `labels.csv` (cal + val)
4. [ ] **0.4** Assemble calibration dataset (avg replicates, common grid, sanity check)
5. [ ] **1.1** Preprocessing toolkit
6. [ ] **1.2** PLS + LOOCV harness
7. [ ] **1.3** Reproduce methods a/b/c → Table 3 — **★ CHECKPOINT (go/no-go)**
8. [ ] **2.1** Build validation set
9. [ ] **2.2** Predict + reproduce Figure 7
10. [ ] **3.2** Interpretability — coefficients hit the chemistry _(headline)_
11. [ ] **3.1** Univariate band-area baseline (motivating floor)
12. [ ] **3.3** Replicate-level group-aware CV (leakage demo)
13. [ ] **3.4** Preprocessing/window search (light, honest)
14. [ ] **3.5** PLS vs PCR/Ridge (brief)
15. [ ] **2.3** _(optional)_ Stage-3 optimize-by-augmentation + critique
16. [ ] **4.1** Consolidate `src/` package
17. [ ] **4.2** Reproduction scripts → `reports/`
18. [ ] **4.4** pytest suite
19. [ ] **4.3** CLI capstone
20. [ ] **4.5** Narrative notebook
21. [ ] **4.6** README
