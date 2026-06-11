"""Composable ATR-IR preprocessing transforms (step 1.1).

Each transform is an sklearn-compatible estimator (``fit``/``transform``), so
recipes are just ``sklearn.pipeline.Pipeline`` objects that drop straight into
the LOOCV harness (1.2) and the window/preprocessing search (3.4). Splitting
``fit`` from ``transform`` is what keeps the pipeline leakage-safe: anything a
transform must learn (e.g. MSC's reference spectrum) is learned on the training
fold inside ``fit`` and merely applied in ``transform``.

Atomic blocks here mirror the six preprocessings in the paper's Table 3
(SNV, MSC, MMN, SLS, LOS, 1st derivative) plus wavenumber-window cropping.
Combined recipes like "1.DER+SLS" are composed as Pipelines, not new classes.
"""

from __future__ import annotations

import numpy as np
from scipy.signal import savgol_filter
from sklearn.base import BaseEstimator, TransformerMixin

# Spectra are stored as X of shape (n_samples, n_channels): one spectrum per row,
# one wavenumber per column. Every transform below operates per-row (axis=1),
# because each measurement is corrected against itself, not against its neighbours.


class _StatelessTransform(BaseEstimator, TransformerMixin):
    """Base for transforms that learn nothing from the training set.

    They correct each spectrum using only its own values, so ``fit`` has no
    statistics to remember -- it just returns ``self`` (sklearn still requires a
    fittable estimator). Subclasses implement ``transform`` only. MSC, which
    *does* learn a reference, deliberately does **not** inherit this -- its
    ``fit`` is the whole point.
    """

    def fit(self, X, y=None):
        return self


class StandardNormalVariate(_StatelessTransform):
    """SNV: centre and scale each spectrum by its *own* mean and std.

    A per-row scatter correction. Subtracting the row mean removes an additive
    baseline offset; dividing by the row std removes a multiplicative scale
    difference (path length / how densely the powder packs against the ATR
    crystal). Stateless -- inherits the no-op ``fit`` from ``_StatelessTransform``.
    """

    def transform(self, X):
        X = np.asarray(X, dtype=float)
        # keepdims=True -> mean/std stay shape (n_samples, 1) so they broadcast
        # down each row against X's (n_samples, n_channels). Without it they'd be
        # 1-D (n_samples,) and the subtraction would fail to align to the columns.
        mean = X.mean(axis=1, keepdims=True)
        std = X.std(axis=1, keepdims=True)
        return (X - mean) / std


class MultiplicativeScatterCorrection(BaseEstimator, TransformerMixin):
    """MSC: correct each spectrum's scatter against a learned reference spectrum.

    Where SNV uses each row's own mean/std, MSC is *model-based*: it fits each
    spectrum to a reference by ordinary least squares, ``x ≈ a + b·ref``, then
    removes the estimated additive (``a``) and multiplicative (``b``) scatter via
    ``(x - a) / b``. The reference is the mean spectrum of the *training* set --
    a genuine cross-sample statistic -- so MSC is the one transform here that
    learns state in ``fit``. Storing it in ``fit`` (not recomputing in
    ``transform``) is what keeps it leakage-safe: test spectra are corrected
    against the training reference only.
    """

    def fit(self, X, y=None):
        X = np.asarray(X, dtype=float)
        self.reference_ = X.mean(axis=0)  # mean spectrum across training samples, (n_channels,)
        return self

    def transform(self, X):
        X = np.asarray(X, dtype=float)
        ref = self.reference_
        ref_c = ref - ref.mean()              # centre the reference once
        denom = ref_c @ ref_c                 # = sum of squares of centred ref (scalar)

        # Per-row OLS of x onto [1, ref], done vectorised across all spectra at once.
        Xc = X - X.mean(axis=1, keepdims=True)
        slope = (Xc @ ref_c) / denom                     # b for each spectrum, (n_samples,)
        intercept = X.mean(axis=1) - slope * ref.mean()  # a for each spectrum, (n_samples,)

        # [:, None] lifts the per-row scalars to (n_samples, 1) so they broadcast
        # back across the columns -- same broadcasting trick as SNV's keepdims.
        return (X - intercept[:, None]) / slope[:, None]


class MinMaxNormalization(_StatelessTransform):
    """MMN: rescale each spectrum so its own min -> 0 and max -> 1.

    OPUS's minimum-maximum normalization. Like SNV it's a per-row rescaling that
    flattens sample-to-sample intensity differences, but anchored to the row's
    extremes instead of its mean/std. Best-effort reproduction of the closed
    OPUS step. Stateless -- inherits the no-op ``fit``.
    """

    def transform(self, X):
        X = np.asarray(X, dtype=float)
        lo = X.min(axis=1, keepdims=True)   # per-row minimum, (n_samples, 1)
        hi = X.max(axis=1, keepdims=True)   # per-row maximum, (n_samples, 1)
        return (X - lo) / (hi - lo)


class SavitzkyGolayDerivative(_StatelessTransform):
    """1.DER: 1st derivative via a Savitzky-Golay filter (smooth + differentiate).

    OPUS's "1st derivative". Savitzky-Golay fits a low-order polynomial to a
    sliding window of points and reports that polynomial's derivative at the
    window centre -- so it differentiates *and* smooths in one pass. That matters
    because a raw finite-difference derivative amplifies noise badly. The 1st
    derivative also removes a constant baseline offset and sharpens overlapping
    bands into resolvable features.

    ``window_length`` (odd) and ``polyorder`` set the filter's shape. OPUS's
    exact settings aren't recalled, so they're tunable -- pinned against Table 3
    at 1.3, searched at 3.4. Stateless: the filter is fixed, nothing is learned.
    """

    def __init__(self, window_length: int = 11, polyorder: int = 2):
        # sklearn contract: __init__ ONLY stores the given params, unchanged, under
        # the same names -- no validation, no derived attributes. That's what lets
        # get_params / clone introspect and rebuild the estimator, which is how
        # GridSearchCV (3.4) sweeps these values. Any real work waits for transform.
        self.window_length = window_length
        self.polyorder = polyorder

    def transform(self, X):
        X = np.asarray(X, dtype=float)
        # deriv=1 -> first derivative; axis=1 -> along wavenumbers, per spectrum.
        return savgol_filter(X, window_length=self.window_length,
                             polyorder=self.polyorder, deriv=1, axis=1)


class StraightLineSubtraction(_StatelessTransform):
    """SLS: subtract a least-squares straight line from each spectrum.

    OPUS's straight-line subtraction -- a 1st-order baseline removal. Fits
    ``y = m·index + c`` to each spectrum by least squares across the channels and
    subtracts it, taking out a sloping baseline (tilt + offset together).

    Subtlety: a baseline is defined against the *wavenumber* axis, but inside a
    Pipeline a transform only sees ``X``. Fitting against channel index instead
    is equivalent here because our grid is uniformly spaced (0.713 cm-1 steps) --
    a uniform rescaling of the x-axis only rescales the slope, which the fit
    absorbs. So SLS stays X-only and needs no wavenumber vector. Best-effort
    reproduction of the closed OPUS algorithm.
    """

    def transform(self, X):
        X = np.asarray(X, dtype=float)
        n = X.shape[1]
        # Design matrix columns [index, 1]; lstsq fits all spectra at once because
        # X.T is (n_channels, n_samples) -- one right-hand side per spectrum.
        A = np.vstack([np.arange(n), np.ones(n)]).T          # (n_channels, 2)
        coeffs, *_ = np.linalg.lstsq(A, X.T, rcond=None)     # (2, n_samples): [slope, intercept] per row
        baseline = (A @ coeffs).T                            # (n_samples, n_channels)
        return X - baseline


class LinearOffsetSubtraction(_StatelessTransform):
    """LOS: subtract a constant offset from each spectrum (floor -> 0).

    OPUS's linear offset subtraction. The simplest baseline: remove a single
    constant per spectrum (its minimum), lifting the baseline floor to zero
    without touching the slope -- a 0th-order correction, in contrast to SLS's
    sloped line. OPUS's exact definition isn't recalled, so this is best-effort:
    if method b (the only one using LOS) misses Table 3 at the 1.3 checkpoint,
    LOS's form is a prime thing to revisit. Stateless.
    """

    def transform(self, X):
        X = np.asarray(X, dtype=float)
        return X - X.min(axis=1, keepdims=True)   # per-row constant offset removed


class WavenumberWindow(BaseEstimator, TransformerMixin):
    """Keep only the channels inside one or more wavenumber intervals (cropping).

    One mechanism, two jobs: the fixed ``<500 cm-1`` ATR edge-crop, and each
    method's analytical window(s) from Table 3. Method b needs *two disjoint*
    windows (652-1266 & 3013-3683), so ``intervals`` is a list of ``(low, high)``
    pairs whose kept channels are unioned.

    Belongs **first** in every recipe: SNV/MSC/MMN derive per-spectrum statistics
    across the kept channels, so dead edge channels must be dropped before them
    or they poison the normalization.

    The wavenumber axis is fixed and known (from the assembled ``Dataset``), so it
    is passed at construction. The boolean column mask is derived in ``fit`` (not
    ``__init__``) to honour sklearn's "``__init__`` only stores params" contract --
    even though the mask depends on params, not on the training data.
    """

    def __init__(self, wavenumber, intervals):
        self.wavenumber = wavenumber    # (n_channels,) axis aligned to X's columns
        self.intervals = intervals      # list of (low, high) cm-1 pairs to keep

    def fit(self, X, y=None):
        wn = np.asarray(self.wavenumber)
        mask = np.zeros(wn.shape, dtype=bool)
        for low, high in self.intervals:
            mask |= (wn >= low) & (wn <= high)   # union of the requested windows
        self.mask_ = mask
        return self

    def transform(self, X):
        X = np.asarray(X, dtype=float)
        return X[:, self.mask_]   # drop every column outside the kept windows
