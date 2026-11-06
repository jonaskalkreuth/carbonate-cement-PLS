"""No validation sample or replicate reaches calibration fitting."""

import hashlib
from pathlib import Path

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

from src.dataset import Dataset, assemble_dataset, read_labels
from src.loader import group_replicates
from src.methods import MethodSpec
from src.val import group_specimens
from src.validate import validate_method

DATA = Path(__file__).resolve().parent.parent / "data"
CAL_DIR = DATA / "calibration spectra"
VAL_DIR = DATA / "validation spectra"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_no_spectrum_file_shared_between_cal_and_val():
    cal = list(CAL_DIR.iterdir())
    val = list(VAL_DIR.iterdir())
    assert not {p.name for p in cal} & {p.name for p in val}
    assert not {_sha256(p) for p in cal} & {_sha256(p) for p in val}


def test_calibration_samples_are_exactly_the_labelled_ones():
    samples = set(group_replicates(CAL_DIR))
    assert samples == set(read_labels(DATA / "labels.csv"))
    assert not any(s.startswith("JK_V") for s in samples)


def test_calibration_has_one_row_per_sample():
    # Replicates are averaged before LOOCV, so a held-out sample's replicates
    # can never sit in the training fold.
    ds = assemble_dataset(CAL_DIR, DATA / "labels.csv")
    assert len(ds.samples) == len(set(ds.samples)) == ds.X.shape[0] == 12


def test_each_validation_file_belongs_to_one_point():
    paths = [p for ps in group_specimens(VAL_DIR).values() for p in ps]
    assert len(paths) == len(set(paths))


_FIT_INPUTS: list[np.ndarray] = []


class _RecordFit(BaseEstimator, TransformerMixin):
    """Passes X through and records every X it is fitted on."""

    def fit(self, X, y=None):
        _FIT_INPUTS.append(np.asarray(X).copy())
        return self

    def transform(self, X):
        return X


def test_validate_method_never_fits_on_validation_rows():
    rng = np.random.default_rng(0)
    wavenumber = np.arange(5, dtype=float)
    X_cal = rng.random((12, 5))
    cal = Dataset(X=X_cal, y=X_cal @ np.arange(1.0, 6.0), wavenumber=wavenumber,
                  samples=[f"c{i}" for i in range(12)])
    sentinel = 999.0   # no calibration value comes near this
    val = Dataset(X=np.full((3, 5), sentinel), y=np.array([10.0, 20.0, 30.0]),
                  wavenumber=wavenumber, samples=["v0", "v1", "v2"])
    spec = MethodSpec(name="t", window=[(0, 4)], candidates={"rec": [_RecordFit()]},
                      n_components=1)

    _FIT_INPUTS.clear()
    validate_method(spec, cal, val)

    assert _FIT_INPUTS   # the recorder was really called
    assert all(X.max() < sentinel for X in _FIT_INPUTS)
