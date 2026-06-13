"""External validation on the held-out V-discs (step 2.2, reproduces Figure 7).

Step 1.3 scored the methods *in-sample* (LOOCV on the 12 calibration discs), and
those numbers are optimistically biased -- the winning preprocessing was chosen on
the very CV it was reported on. This module is the unbiased judge: fit each method
on all 12 calibration discs, predict the 6 V-discs the model never saw, and measure
how the error grows from RMSECV (cal) to RMSEP (val). That cal->val gap is the
project's headline honesty point.

The paper's Figure 7 has no single RMSEP target; the reproducible targets are the
*trend* (good near 20 wt%, under-estimates mid-range, over-estimates above 47 wt%),
the relative errors (<=8-9% for methods a & c), and the paired t-test p-values
(a:0.526, b:0.241, c:0.730 -- all > 0.05, so "no significant difference from the
reference"). We reproduce the t-test as the one hard numeric check.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import ttest_rel
from sklearn.metrics import r2_score

from src.dataset import Dataset
from src.methods import METHODS, MethodSpec, _compile, select_best


@dataclass(frozen=True)
class ValidationResult:
    """One method's external-validation result on the held-out V-discs.

    Frozen and self-consistent like ``CVResult``: every scalar is computed from the
    ``y_true``/``y_pred`` stored here, so the metrics can never drift from the
    predictions they summarise. ``rmsecv_cal`` is carried over from the calibration
    LOOCV (the search winner's score) purely so the cal->val gap is one subtraction
    away -- it is the headline of this step.
    """

    name: str                  # method label, "a"/"b"/"c"
    winner: str                # winning preprocessing the search picked on cal, e.g. "MSC"
    y_true: np.ndarray         # (6,) TG-FTIR reference CaCO3 wt%, row-aligned to y_pred
    y_pred: np.ndarray         # (6,) predicted CaCO3 wt% from the cal-fitted model
    rmsep: float               # root mean squared error of prediction, wt% (external twin of RMSECV)
    r2_ext: float              # R2 on the 6 held-out discs (pooled, sklearn convention)
    bias: float                # mean signed error (pred - ref): +ve = systematic over-estimate
    relative_error: np.ndarray # (6,) per-disc (pred - ref)/ref * 100, the Figure-7 right panel
    p_value: float             # paired t-test (pred vs ref); > 0.05 => no significant difference
    rmsecv_cal: float          # the winner's calibration RMSECV, for the cal->val gap

    @property
    def gap(self) -> float:
        """RMSEP - RMSECV: how much error the honest external test adds over cal CV."""
        return self.rmsep - self.rmsecv_cal


def score_validation(name: str, winner: str, y_true: np.ndarray, y_pred: np.ndarray,
                     rmsecv_cal: float) -> ValidationResult:
    """Turn one method's V-disc predictions into the full Figure-7 metric set.

    Pure arithmetic -- no models touched here. RMSEP mirrors RMSECV exactly (root of
    the mean squared error) but on the held-out discs, so the two are directly
    comparable. The paired t-test asks the paper's question: across the 6 discs, are
    the prediction errors (pred - ref) centred on zero, or is there a systematic
    shift? A p > 0.05 means we cannot reject "no difference" -- the model is unbiased
    in the statistical sense even where individual discs are off.
    """
    rmsep = float(np.sqrt(np.mean((y_pred - y_true) ** 2)))
    r2_ext = float(r2_score(y_true, y_pred))
    bias = float(np.mean(y_pred - y_true))            # signed, so over/under-estimate shows
    relative_error = (y_pred - y_true) / y_true * 100.0

    # Paired because each predicted value is matched to the reference for the SAME disc;
    # ttest_rel tests whether the mean of the per-disc differences is zero. We keep only
    # the p-value -- the reproduction target (a:0.526 / b:0.241 / c:0.730).
    p_value = float(ttest_rel(y_pred, y_true).pvalue)

    return ValidationResult(
        name=name, winner=winner, y_true=y_true, y_pred=y_pred,
        rmsep=rmsep, r2_ext=r2_ext, bias=bias, relative_error=relative_error,
        p_value=p_value, rmsecv_cal=rmsecv_cal,
    )


def validate_method(spec: MethodSpec, cal: Dataset, val: Dataset) -> ValidationResult:
    """Fit one method on the full calibration set, predict the held-out V-discs.

    The winning preprocessing is *re-derived* on cal (``select_best``, the same
    mechanical search as 1.3) rather than hardcoded, so the val path stays honest
    and independent of 1.3 having run. The winner is then fit on **all 12** cal
    discs (no CV here -- CV was 1.3's job) and used to predict the 6 V-discs.
    """
    selection = select_best(spec, cal.X, cal.y, cal.wavenumber)

    # Build the winner's pipeline and fit it on the WHOLE calibration set. This is the
    # leakage boundary: .fit sees only cal, so MSC's reference spectrum and PLS's loadings
    # are learned from cal alone; the V-discs enter only at .predict and never influence
    # the model. (Contrast 1.3's LOOCV, which had to re-fit per fold because the held-out
    # sample lived inside the same matrix -- here cal and val are physically separate sets.)
    pipeline = _compile(spec.window, spec.candidates[selection.winner],
                        spec.n_components, cal.wavenumber)
    pipeline.fit(cal.X, cal.y)
    y_pred = pipeline.predict(val.X).ravel()   # (6, 1) -> (6,), same as the loocv ravel

    return score_validation(spec.name, selection.winner, val.y, y_pred,
                            rmsecv_cal=selection.cv.rmsecv)


def validate_all(cal: Dataset, val: Dataset) -> list[ValidationResult]:
    """Externally validate every method in ``METHODS`` -> one result each, a/b/c order."""
    return [validate_method(spec, cal, val) for spec in METHODS.values()]
