"""The three published methods a/b/c, as preprocessing *searches* (step 1.3).

OPUS Quant 2 has an automatic preprocessing optimization: it evaluates a set of
candidate preprocessings and reports the one with the best cross-validated error.
So Table 3's "preprocessing" column is read here not as a sequential pipeline but
as the *candidate set Quant 2 searched* -- and the reported model is the winner.

This module encodes that literally: each ``MethodSpec`` holds its window, factor
count, and the listed candidates; ``select_best`` LOOCV-scores every candidate and
picks the lowest-RMSECV one, reproducing Quant 2's optimize. The selection being
mechanical (not hand-picked) is the point -- and it lands the paper: a -> MSC,
b -> SNV, c -> MMN, each the preprocessing its method is built around.

Two reproduction caveats, honestly: (1) OPUS's SLS/LOS/MMN/derivative are closed,
so absolute RMSECV matches only within a best-effort gap ("match the result, not
the bits", spec decision 5) -- method b's winner even slightly *beats* the paper.
(2) Selecting preprocessing by LOOCV at n=12 is itself the optimism trap this
project exists to expose; we reproduce it faithfully here and let external
validation (2.2) be the real judge.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.base import BaseEstimator
from sklearn.cross_decomposition import PLSRegression
from sklearn.pipeline import Pipeline, make_pipeline

from src.pls import CVResult, SweepResult, loocv, sweep_factors
from src.preprocessing import (
    LinearOffsetSubtraction,
    MinMaxNormalization,
    MultiplicativeScatterCorrection,
    SavitzkyGolayDerivative,
    StandardNormalVariate,
    StraightLineSubtraction,
    WavenumberWindow,
)

# Global preprocessing settings pinned at the 1.3 checkpoint (shared by all
# methods, so not part of any one MethodSpec):
#   - SG derivative: OPUS's "1st derivative" reproduced as a 21-point quadratic
#     Savitzky-Golay filter (smooths while differentiating; searched at 3.4).
#   - PLS_SCALE=False: OPUS Quant mean-centres but does not unit-variance scale
#     each channel; scale=True inflates noise-dominated channels (~2x RMSECV).
SG_WINDOW_LENGTH = 21
SG_POLYORDER = 2
PLS_SCALE = False


def _derivative() -> SavitzkyGolayDerivative:
    """The pinned 1st-derivative filter, a fresh instance per candidate."""
    return SavitzkyGolayDerivative(window_length=SG_WINDOW_LENGTH, polyorder=SG_POLYORDER)


@dataclass(frozen=True)
class MethodSpec:
    """One Table-3 method: its window(s), the candidate preprocessings, factors.

    ``candidates`` maps a label (as the paper lists it, e.g. ``"1.DER+SLS"``) to
    the ordered transformer instances that realise it -- so it reads as a literal
    transcription of the Table-3 column, and is the search space ``select_best``
    ranks. The instances carry no fitted state; each is cloned per CV fold, so
    reusing one spec across all 12 folds stays leakage-free.
    """

    name: str                                       # method label, e.g. "a"
    window: list[tuple[float, float]]               # wavenumber interval(s) kept, cm-1
    candidates: dict[str, list[BaseEstimator]]      # label -> preprocessing steps
    n_components: int                               # PLS factors the paper pinned


def _compile(window: list[tuple[float, float]], steps: list[BaseEstimator],
             n_components: int, wavenumber: np.ndarray) -> Pipeline:
    """Build one runnable pipeline: crop -> the candidate's steps -> PLS.

    Crop first (``WavenumberWindow``) so per-spectrum scatter stats see only the
    kept channels (1.1 reasoning); PLS last at the pinned factor count. The
    wavenumber axis lives on the ``Dataset``, not the spec, so it is passed here.
    """
    window_step = WavenumberWindow(wavenumber, window)
    pls = PLSRegression(n_components=n_components, scale=PLS_SCALE)
    return make_pipeline(window_step, *steps, pls)


@dataclass(frozen=True)
class Selection:
    """Quant 2's preprocessing search reproduced over one method's candidates.

    ``ranking`` is every candidate scored and sorted best-RMSECV-first; ``winner``
    and ``cv`` are just its head, kept explicit so callers need not re-sort.
    """

    winner: str                         # winning candidate label
    cv: CVResult                        # winner's LOOCV at the pinned factor count
    ranking: list[tuple[str, CVResult]] # (label, result) sorted by ascending RMSECV


def select_best(spec: MethodSpec, X: np.ndarray, y: np.ndarray,
                wavenumber: np.ndarray) -> Selection:
    """LOOCV-score every candidate and pick the lowest RMSECV -- Quant 2's optimize.

    Selecting on the CV metric is exactly the optimism trap (caveat 2 in the module
    docstring); reproduced deliberately, because it is what the software did.
    """
    scored = [(label, loocv(_compile(spec.window, steps, spec.n_components, wavenumber), X, y))
              for label, steps in spec.candidates.items()]
    scored.sort(key=lambda lc: lc[1].rmsecv)   # Quant 2 ranks candidates by RMSECV
    winner, cv = scored[0]
    return Selection(winner=winner, cv=cv, ranking=scored)


# The three methods as candidate sets, transcribed straight from Table 3's
# preprocessing column. "1.DER+SLS" is one candidate realised as two steps.
METHODS: dict[str, MethodSpec] = {
    "a": MethodSpec(
        name="a",
        window=[(683, 1620)],
        candidates={
            "SNV": [StandardNormalVariate()],
            "SLS": [StraightLineSubtraction()],
            "MSC": [MultiplicativeScatterCorrection()],
            "1.DER+SLS": [_derivative(), StraightLineSubtraction()],
        },
        n_components=4,
    ),
    "b": MethodSpec(
        name="b",
        window=[(652, 1266), (3013, 3683)],   # two disjoint analytical windows
        candidates={
            "LOS": [LinearOffsetSubtraction()],
            "SNV": [StandardNormalVariate()],
            "MSC": [MultiplicativeScatterCorrection()],
            "1.DER": [_derivative()],
        },
        n_components=4,
    ),
    "c": MethodSpec(
        name="c",
        window=[(652, 1266)],
        candidates={
            "MMN": [MinMaxNormalization()],
            "SLS": [StraightLineSubtraction()],
            "MSC": [MultiplicativeScatterCorrection()],
            "1.DER+SLS": [_derivative(), StraightLineSubtraction()],
        },
        n_components=3,
    ),
}


@dataclass(frozen=True)
class PaperResult:
    """The published Table-3 numbers for one method -- the reproduction target."""

    r2: float            # R² as printed in the paper, percent (e.g. 99.52)
    rmsecv: float        # RMSECV in wt%
    n_components: int    # PLS factor count the paper reported


PAPER_TABLE3: dict[str, PaperResult] = {
    "a": PaperResult(r2=99.52, rmsecv=1.38, n_components=4),
    "b": PaperResult(r2=99.62, rmsecv=1.10, n_components=4),
    "c": PaperResult(r2=99.47, rmsecv=1.34, n_components=3),
}

# Success bar (SPEC decision #8). R² floor + a *symmetric* RMSECV tolerance: the
# honest "did we land where the paper landed?" test. Being better than the paper
# by more than the tolerance is reported as "beats", not a pass -- but it does not
# block the checkpoint, since beating the reference is no reason to halt.
R2_FLOOR_PCT = 99.0
RMSECV_TOL_WTPCT = 0.3


@dataclass(frozen=True)
class MethodComparison:
    """One method's reproduction (the search winner) set against its paper target."""

    name: str
    selection: Selection   # the preprocessing search result; .cv is the winner's
    sweep: SweepResult     # factor sweep on the winner, for the "CV would pick" column
    paper: PaperResult

    @property
    def cv(self) -> CVResult:
        """The winning candidate's LOOCV result."""
        return self.selection.cv

    @property
    def r2_pct(self) -> float:
        """Our pooled R² on the paper's 0–100 scale (sklearn returns a fraction)."""
        return self.cv.r2 * 100.0

    @property
    def rmsecv_delta(self) -> float:
        """Ours − paper, wt%. Positive = we are worse; negative = we beat the paper."""
        return self.cv.rmsecv - self.paper.rmsecv

    @property
    def verdict(self) -> str:
        """'match' (within ±tol), 'beats' (better than paper by >tol), or 'miss'."""
        if self.r2_pct < R2_FLOOR_PCT or self.rmsecv_delta > RMSECV_TOL_WTPCT:
            return "miss"
        if self.rmsecv_delta < -RMSECV_TOL_WTPCT:
            return "beats"
        return "match"

    @property
    def blocks_go(self) -> bool:
        """A method blocks the checkpoint only if it is worse than the paper (a miss)."""
        return self.verdict == "miss"


def reproduce_method(spec: MethodSpec, X: np.ndarray, y: np.ndarray,
                     wavenumber: np.ndarray, max_components: int = 8) -> MethodComparison:
    """Run the preprocessing search, then factor-sweep the winner vs its target."""
    selection = select_best(spec, X, y, wavenumber)
    winner_pipeline = _compile(spec.window, spec.candidates[selection.winner],
                               spec.n_components, wavenumber)
    sweep = sweep_factors(winner_pipeline, X, y, max_components)
    return MethodComparison(name=spec.name, selection=selection, sweep=sweep,
                            paper=PAPER_TABLE3[spec.name])


def reproduce_all(X: np.ndarray, y: np.ndarray, wavenumber: np.ndarray,
                  max_components: int = 8) -> list[MethodComparison]:
    """Run every method in ``METHODS`` -> one comparison each, in a/b/c order."""
    return [reproduce_method(spec, X, y, wavenumber, max_components)
            for spec in METHODS.values()]
