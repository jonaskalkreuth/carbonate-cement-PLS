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
    - [x] **0.2 OPUS loader** (`src`) — parse OPUS binary → (wavenumber, absorbance) from `'a'` block; discover + group replicate files per sample. _why leaf: block + grouping decided, just implement._  ✅ `src/loader.py`: frozen `Spectrum` dataclass + `load_spectrum` (ascending wn, 5049 pts) + `group_replicates` (regex `\.\d+$`); verified 12 cal samples × 3 replicates, .DS_Store filtered.
    - [x] **0.3 Label extraction → committed `labels.csv`** — parse `Auswertung…xlsx`, map sample → FTIR CaCO₃ wt%, write the one published derived file. _why leaf: source + target decided._  ✅ `scripts/extract_labels.py` → `data/labels.csv`: 12 cal samples `JK_MV_01..12`, FTIR CaCO₃ (col U); names map 1-to-1 to loader keys; val labels deferred to 2.1.
    - [x] **0.4 Assemble modelling dataset** — average replicates per sample, resample to common wavenumber grid, align X with y, sanity check (overlay plot + label range). _why leaf: average + common-grid decided._  ✅ `src/dataset.py`: frozen `Dataset` + `assemble_dataset` → X (12, 5049), y (12,), CaCO₃ 2.45–61.26 wt%; B1 axis-guard (all 36 spectra bit-identical axis, no interpolation), X/y aligned by sample key. `scripts/check_dataset.py` overlay confirms carbonate ν₃/ν₂ bands deepen with wt%; <500 cm⁻¹ ATR edge-noise to be cropped at 1.3.
  - **Phase 1 — Reproduce core** *(the de-risking checkpoint)*
    - [x] **1.1 Preprocessing toolkit** (`src`) — composable transforms: SNV, MSC, Savitzky-Golay 1st-deriv (exact) + OPUS best-effort SLS/LOS/MMN + spectral-window cropping. _why leaf: "match result not bits" decided; just implement._  ✅ `src/preprocessing.py`: 6 sklearn transformers (`BaseEstimator`+`TransformerMixin`) — SNV/MMN/MSC, SG 1.DER (parametrised), SLS/LOS (best-effort) — on a `_StatelessTransform` base; MSC is the only one that learns state (`fit` → training mean spectrum, leakage-safe). `WavenumberWindow` crops a *list* of intervals (method b's two disjoint windows) and runs first. Verified: all 6 finite on real X; method-a recipe composes through 6 stages → (12, 1314); combo semantics still deferred to 1.3.
    - [x] **1.2 PLS + LOOCV harness** (`src`) — sklearn PLSRegression, leave-one-out CV, R²/RMSECV, RMSECV-vs-#factors curve. _why leaf: model + CV scheme decided._  ✅ `src/pls.py`: frozen `CVResult` + `loocv` (`cross_val_predict`/`LeaveOneOut`, leakage-safe via per-fold Pipeline re-fit, R² pooled over 12 held-out preds, RMSECV in wt%) + `sweep_factors`→`SweepResult` (curve + argmin + one-SE parsimony pick, computed in MSE units). `scripts/plot_rmsecv_curve.py` renders the U-curve (PNG gitignored). Demo crop+SNV recipe: clean U, dip + one-SE both at 3 factors, RMSECV 0.90 wt% — harness works; real recipes/pinned counts are 1.3.
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
- **0.1 — data staging:** commit all 36 calibration + 63 validation OPUS files (~9 MB, flat binary files named `JK_*.N` where `.N` = replicate). Gitignore the 3 Excel files + `.DS_Store` + artifacts **before** the first commit.
- **0.1 — dirs:** `src/ tests/ scripts/ notebooks/ reports/ models/ data/` (matches project 1).

### 0.2 — OPUS loader (`src/loader.py`)
- **Return type (A2):** frozen `@dataclass Spectrum(wavenumber, absorbance, source: Path)` from the OPUS `'a'` block. _Chosen over a bare tuple (no provenance) and over project-1's DataFrame style (heavyweight for two aligned vectors); `source` pays off when debugging which replicate looks off._
- **Orientation:** `load_spectrum(path) -> Spectrum` flips wavenumber to **ascending** (400→3998) via `argsort` at the single point of entry, so the whole pipeline sees one orientation. Spectroscopy high→low is a display-time flip only.
- **Grouping:** `group_replicates(dir) -> dict[str, list[Path]]`, key = sample root via regex `r"\.\d+$"` (strip trailing `.N`). Dict key is just the bucket label; full replicate paths preserved in the list. Regex (not `Path.stem`) for safety on irregular names like `JK_V2_Test.0`.
- **Scope boundary:** 0.2 loads one file + groups paths only. **Averaging / common-grid resampling deferred to 0.4.**
- **API facts (probed):** `read_opus(path).a.x` = wavenumber descending 3998→400, `.a.y` = absorbance, 5049 pts; files may also carry an `a_2` block — we take `a`. Cal = 12 clean roots `JK_MV_01..12`; validation naming irregular (handled in 2.1).

### 0.3 — Label extraction (`scripts/extract_labels.py` → `data/labels.csv`)
- **Source sheet:** `Auswertung TG-FTIR-ATR-Kalibrierung.xlsx`, single sheet `TG-FTIR NEU NEU`. Right-hand summary table (`Probe 1..12`) is one clean row per sample; its values equal the per-sample `MITTELWERT` of the left block.
- **Name mapping (resolved):** trivial 1-to-1 — `Probe N` ↔ `JK_MV_{N:02d}`, matching the loader's group keys. No fuzzy matching.
- **Reference y (resolved):** **FTIR CaCO₃** (col U) = CaCO₃ from evolved-CO₂ peak area. _Chosen over TG-mass-loss CaCO₃ (col W) and over nominal/expected (cols S/T, which are recipe targets, not measurements). Decisive reason: the sheet's "IN QUANT" blocks show the U values are the concentrations that were copied into OPUS Quant, so U is the apples-to-apples reproduction target._ FTIR vs TG agree within ~1–2 wt%.
- **Provenance:** extraction is a committed script (raw Excel stays gitignored), so each label traces back to a sheet+column rather than being hand-typed.
- **Scope:** calibration labels only; the 12 `JK_MV_*` references live in this sheet. Validation (`JK_V*`) references are elsewhere and are deferred to 2.1.
- **⚠ Caveat (reproduction-checkpoint flag):** a separate post-thesis Excel (`Berechnung CO2-Uptake.xlsx`) holds *newer* CO₂-uptake / CaCO₃ values produced for the publication. Per the user's recollection these were used only to re-determine CO₂ absorbed — the OPUS PLS models were **not** retrained — so this calibration sheet's values are the right reproduction target. **If the 1.3 checkpoint comes out further from the paper than expected, the newer CaCO₃ values are the first thing to re-check.**
- **Calibration range (resolved, not a flag):** `labels.csv` spans 2.45–61.26 wt%, wider than the paper's "~20–48 wt%". Confirmed against the thesis: 20–48 wt% is the **external-validation** window only; the PLS calibration was fit on **all 12 JK_MV samples** across the full range. So the wide span is correct and expected — do *not* treat it as a divergence at the 1.3 checkpoint.

### 0.4 — Assemble dataset (`src/dataset.py`)
- **Return type (C2):** frozen `@dataclass Dataset(X, y, wavenumber, samples)` — same instinct as `Spectrum`; binds aligned arrays + provenance, unwrapped as `ds.X, ds.y` at the sklearn boundary. _Chosen over bare NumPy + names list (arrays travel unbound) and a 5049-col DataFrame (heavyweight, immediately `.values`-ed back; 0.2 already rejected the DataFrame style)._
- **Common grid (B1):** assert-identical guard, **no interpolation**. Probed all 36 cal spectra: bit-identical 5049-pt axis (399.95→3998.76, uniform 0.713 cm⁻¹, zero deviation), so `_mean_spectrum` raises on any axis mismatch rather than resampling. _Chosen over always-interpolate (needless interpolation error here) and a guard+interpolate seam (YAGNI). If 2.1's validation spectra sit on a different axis, that's the moment to add `np.interp` — with real data in hand._
- **X/y alignment:** by sample **key**, not position. `samples = list(groups)` is the single source of truth for row order; X and y are both comprehensions over it, `y` via `labels[s]` lookup. Position-zipping would misalign silently if CSV/loader order diverged; a missing label raises `KeyError` loudly instead.
- **Averaging:** elementwise mean over a sample's replicate vectors, `np.mean(np.vstack(rows), axis=0)` → one row per sample (12 rows).
- **Invariants:** assert X/y shapes + all-finite at assembly end — cheap contract before anything reaches PLS.
- **Persistence:** none — pure in-memory rebuild (12 means from 36 files is ~ms; a cached `.npz` is just an invalidation risk).
- **Sanity check:** `scripts/check_dataset.py` overlays the 12 mean spectra coloured by CaCO₃ wt%; carbonate bands deepening with concentration is the visual proof X/y are correctly paired. Output PNG gitignored (regenerable).

### 1.1 — Preprocessing toolkit (`src/preprocessing.py`)
- **Architecture (the fork → B):** each transform is an **sklearn-compatible transformer** (`BaseEstimator` + `TransformerMixin`, `fit`/`transform`); recipes are sklearn `Pipeline`s. _Chosen over (A) plain functions — leakage discipline falls on us, no CV integration — and (C) a hand-rolled `Transform` protocol — reinvents `Pipeline`. Decisive reason: per-fold `fit` makes **MSC's reference spectrum leakage-safe by construction**, and recipes drop straight into the 1.2 LOOCV harness and the 3.4 `GridSearchCV` window/preprocessing search. Cost is ~3 lines of boilerplate per transform (`__init__`/`fit`/`transform`)._
- **Six atomic transforms = union across methods a/b/c:** `LOS` (linear offset subtraction), `SLS` (straight-line subtraction), `SNV`, `MMN` (min-max normalization), `MSC`, `1.DER` (Savitzky–Golay 1st derivative, `scipy.signal.savgol_filter`). `1.DER+SLS` is **not** a 7th transform — it's a two-step `Pipeline([Derivative, SLS])`. _Composition is free under B._
- **Fidelity:** SNV / MSC / SG-derivative **exact**; OPUS `SLS`/`LOS`/`MMN` **best-effort** (closed algorithms — "match result not bits", spec decision 5). `MSC` is the only transform whose `fit` learns state (the reference = training-fold mean spectrum); the rest have a no-op `fit`.
- **Cropping = one axis-aware transform** taking a **list** of `(low, high)` intervals (method b needs two disjoint windows: 652–1266 **&** 3013–3683), building a boolean column-mask at construction from the wavenumber axis. Subsumes the `<500 cm⁻¹` ATR edge-crop (same op, different intervals). **Runs first in every recipe** (before scatter/normalization/derivative): SNV/MSC compute per-spectrum stats across the included channels, so edge-noise must be gone first or it distorts the whole normalized spectrum. Matches the thesis (spectra were cropped right after measurement).
- **Table 3 targets (recorded here for 1.3 wiring):** a = {SNV, SLS, MSC, 1.DER+SLS} / 683–1620 / 4 factors / R² 99.52 / RMSECV 1.38 · b = {LOS, SNV, MSC, 1.DER} / 652–1266 & 3013–3683 / 4 / 99.62 / 1.1 · c = {MMN, SLS, MSC, 1.DER+SLS} / 652–1266 / 3 / 99.47 / 1.34.
- **⚠ Combo semantics unresolved (1.3 task, not 1.1):** the paper lists four preprocessings per method but reports one model each; OPUS's exact combination logic isn't recalled and Quant 2 is closed. **Resolve empirically at 1.3:** try the listed order as a sequential `Pipeline` first, best-of-singles as fallback, and keep whichever reproduces the Table 3 metrics. This is the "match the result, not the bits" method, and exactly what architecture B was chosen to make cheap. 1.1 builds the six composable blocks; it does **not** wire the recipes.

### 1.2 — PLS + LOOCV harness (`src/pls.py`)
- **Engine (the fork → B, with A as teaching scaffold):** leave-one-out CV via sklearn **`cross_val_predict`** (`cv=LeaveOneOut()`), which returns the 12 held-out predictions directly and is leakage-safe by construction (re-fits the *whole* Pipeline each fold, so MSC's reference is learned on the 11 training samples only). _Chosen over (A) a hand-rolled fold loop — more visible but more code; we build it once as a teaching X-ray then collapse to B — and (C) `cross_validate`/`cross_val_score`, which return per-fold scores not predictions, losing the 12 aligned held-out values we need for pooled R² and for the 2.2 Figure-7 predicted-vs-reference plot._
- **Metrics:** **RMSECV** = `sqrt(mean((y − y_cv)²))` (root mean squared held-out error, divided by *n*=12 — the chemometrics convention the paper reports, **not** n−factors). **R² pooled over all 12** held-out predictions via `r2_score(y, y_cv)`, not averaged per-fold — pooling matches OPUS's cross-validated R².
- **Factor sweep:** run the engine across `n_components = 1…k`, returning the full **RMSECV-vs-#factors curve** + the raw **argmin** (lowest dip) + the **one-standard-error pick** (simplest model within 1 SE of the best — parsimony guard against CV overfitting at small n). The sweep *proposes*; it is a diagnostic, not an autopilot.
- **Reproduce-first stance (resolves the user's "check for better options"):** 1.3 pins the paper's **exact** factor count per method for an apples-to-apples Table 3 comparison; the sweep's argmin/one-SE picks are reported *alongside* as "what our CV would have chosen", never substituted. **Whether anything is genuinely "better" is judged by external validation (2.2 / V-samples), not by the LOOCV number** — choosing factors by min-RMSECV at n≈12 is the exact optimism trap the project exists to expose. Improvement work proper lives in extensions 3.4/3.5.
- **API shape:** results travel in **frozen dataclasses** (house style, like `Spectrum`/`Dataset`) — a `CVResult(y_true, y_pred, r2, rmsecv, n_components)` binding the aligned arrays to their metrics, and a small sweep-result holding the curve + suggested picks. _Keeps the wrong predictions from ever being paired with the wrong samples._
- **Plot home:** RMSECV-vs-#factors curve drawn by a `scripts/` helper (mirrors `check_dataset.py`), keeping `src/` pure compute with no matplotlib import side-effects. PNG gitignored (regenerable).

## Next up
> Ordered for reproduction-first build; reorder freely. The **checkpoint at #7** is the go/no-go — don't invest in packaging until the numbers reproduce.

1. [x] **0.1** Repo scaffolding & data staging
2. [x] **0.2** OPUS loader
3. [x] **0.3** Label extraction → `labels.csv` (cal; val deferred to 2.1)
4. [x] **0.4** Assemble calibration dataset (avg replicates, common grid, sanity check)
5. [x] **1.1** Preprocessing toolkit
6. [x] **1.2** PLS + LOOCV harness
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
