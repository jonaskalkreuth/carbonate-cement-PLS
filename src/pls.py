"""PLS + leave-one-out cross-validation harness (step 1.2).

The measuring instrument for the reproduction: given a preprocessing-plus-PLS
``Pipeline`` and the calibration ``(X, y)``, score it the way the paper does --
leave-one-out CV, R² pooled over the held-out predictions, RMSECV in wt% -- and
sweep the factor count to draw the RMSECV-vs-#factors curve.

Leakage safety is inherited from the Pipeline boundary: ``cross_val_predict``
re-fits the *whole* pipeline on each fold's 11 training samples, so MSC's
reference spectrum (step 1.1) is learned without ever seeing the held-out sample.
This harness wires no chemistry; method-specific recipes + factor counts are
pinned in step 1.3.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.base import clone
from sklearn.cross_decomposition import PLSRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.pipeline import Pipeline


@dataclass(frozen=True)
class CVResult:
    """One model's leave-one-out result: the held-out predictions + their scores.

    Frozen and self-consistent, like ``Dataset``: ``y_pred[i]`` is the prediction
    a model made for sample ``i`` while that sample was held out, and ``r2`` /
    ``rmsecv`` are computed from exactly these arrays -- so the metrics can never
    drift away from the predictions they summarise.
    """

    n_components: int       # PLS factor count this result was scored at
    y_true: np.ndarray      # (n_samples,) reference CaCO3 wt%, row-aligned to y_pred
    y_pred: np.ndarray      # (n_samples,) leave-one-out predicted CaCO3 wt%
    r2: float               # R² pooled over all held-out predictions
    rmsecv: float           # root mean squared error of cross-validation, wt%


def loocv(pipeline: Pipeline, X: np.ndarray, y: np.ndarray) -> CVResult:
    """Leave-one-out cross-validate a preprocessing+PLS pipeline on ``(X, y)``.

    ``cross_val_predict`` runs the same loop we wrote by hand -- 12 folds, a fresh
    clone fitted on 11 samples, the 12th predicted -- and returns the held-out
    predictions in original row order, so ``y`` and the predictions stay aligned.
    """
    # cv=LeaveOneOut() => one fold per sample. The returned array is (n_samples, 1)
    # because PLSRegression predicts a column vector; ravel() flattens it to 1-D so
    # it lines up with y and with CVResult's 1-D contract.
    y_pred = cross_val_predict(pipeline, X, y, cv=LeaveOneOut()).ravel()

    # r2_score over ALL held-out predictions at once (pooled), not averaged per fold
    # -- with one test sample per fold a per-fold R² is undefined anyway. RMSECV is
    # the root of the mean squared held-out error, in wt%, divided by n (paper's
    # convention), which is exactly what mean() does here.
    r2 = r2_score(y, y_pred)
    rmsecv = float(np.sqrt(np.mean((y - y_pred) ** 2)))

    # n_components lives on the final pipeline step; record it so the result is
    # self-describing without the caller having to remember what it passed.
    n_components = pipeline.steps[-1][1].n_components
    return CVResult(n_components=n_components, y_true=y, y_pred=y_pred, r2=r2, rmsecv=rmsecv)


@dataclass(frozen=True)
class SweepResult:
    """RMSECV-vs-#factors curve plus two suggested factor counts.

    A diagnostic, not an autopilot (design 1.2): ``best`` is the raw lowest dip,
    ``parsimonious`` is the one-standard-error pick. Step 1.3 still pins the
    paper's factor count explicitly and reports these alongside.
    """

    results: list[CVResult]   # one CVResult per factor count, ascending n_components
    best: int                 # n_components at the lowest RMSECV (argmin)
    parsimonious: int         # fewest factors within 1 SE of the best (one-SE rule)

    @property
    def n_components(self) -> np.ndarray:
        """The factor-count axis of the curve."""
        return np.array([r.n_components for r in self.results])

    @property
    def rmsecv(self) -> np.ndarray:
        """The RMSECV value at each factor count (the curve itself)."""
        return np.array([r.rmsecv for r in self.results])


def sweep_factors(pipeline: Pipeline, X: np.ndarray, y: np.ndarray,
                  max_components: int) -> SweepResult:
    """Leave-one-out score ``pipeline`` at n_components = 1 … ``max_components``.

    Re-runs ``loocv`` once per factor count, cloning ``pipeline`` each time and
    overriding only the final PLS step's ``n_components`` -- so the preprocessing
    recipe is held fixed while the one dial we care about is swept.
    """
    pls_name = pipeline.steps[-1][0]   # name of the final step, e.g. "pls"

    results = []
    for k in range(1, max_components + 1):
        # clone -> fresh unfitted copy; set_params with the "<step>__<param>" key
        # reaches into the named step and overrides just its n_components. Cloning
        # per k keeps each sweep point independent (no fitted state carried over).
        candidate = clone(pipeline).set_params(**{f"{pls_name}__n_components": k})
        results.append(loocv(candidate, X, y))

    # Work in mean-squared-error (wt%²) for the selection, then the RMSECV curve is
    # just its square root. Doing the one-SE arithmetic on MSE keeps units consistent:
    # an error bar on a mean belongs on the same scale as that mean.
    mse = np.array([r.rmsecv ** 2 for r in results])
    best_idx = int(np.argmin(mse))                    # lowest dip (same as argmin RMSECV)

    # One-standard-error rule: each held-out squared error is one observation of the
    # model's squared error, so MSECV = their mean and we can put a standard error on it
    # (std / sqrt(n)). Threshold = best MSE + 1 SE; pick the FEWEST factors whose MSE sits
    # under it. Rationale: at n=12 the curve is noisy, so a model within noise of the best
    # but simpler is the safer bet -- fewer factors, less room to overfit.
    best = results[best_idx]
    sq_errors = (best.y_true - best.y_pred) ** 2
    se = float(np.std(sq_errors, ddof=1) / np.sqrt(sq_errors.size))   # SE of the mean squared error
    threshold = mse[best_idx] + se
    parsimonious_idx = int(np.argmax(mse <= threshold))   # argmax of a bool array = first True = fewest factors

    return SweepResult(
        results=results,
        best=results[best_idx].n_components,
        parsimonious=results[parsimonious_idx].n_components,
    )
