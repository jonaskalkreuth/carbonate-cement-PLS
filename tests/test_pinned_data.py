"""Pinned data: the committed label files match their recorded references."""

from pathlib import Path

import pytest

from src.dataset import read_labels

DATA = Path(__file__).resolve().parent.parent / "data"

# The five reference values recorded from the OPUS .q2 method files
# (reports/2.2_preprocessing-order-investigation.md, "Update 2"), at 2 dp.
Q2_REFERENCE = {
    "JK_MV_01": 2.45,
    "JK_MV_03": 15.54,
    "JK_MV_02": 33.62,
    "JK_MV_09": 44.32,
    "JK_MV_06": 61.27,
}

# Snapshot of all 12 committed calibration labels, so any edit to labels.csv fails loudly.
LABELS_SNAPSHOT = {
    "JK_MV_01": 2.4502,
    "JK_MV_02": 33.6241,
    "JK_MV_03": 15.54,
    "JK_MV_04": 48.9673,
    "JK_MV_05": 22.395,
    "JK_MV_06": 61.2646,
    "JK_MV_07": 39.3248,
    "JK_MV_08": 27.5725,
    "JK_MV_09": 44.3174,
    "JK_MV_10": 8.8477,
    "JK_MV_11": 56.3846,
    "JK_MV_12": 11.2078,
}

FIGURE7_POINTS = ["JK_V1_1", "JK_V1_2", "JK_V2_1", "JK_V2_2", "JK_V3_1", "JK_V3_2", "JK_V4", "JK_V5"]


def test_labels_match_recorded_q2_values():
    # Tolerance 0.01 wt%: JK_MV_06 is 61.2646 in labels.csv but recorded as 61.27.
    labels = read_labels(DATA / "labels.csv")
    for sample, q2 in Q2_REFERENCE.items():
        assert labels[sample] == pytest.approx(q2, abs=0.01), sample


def test_labels_snapshot():
    assert read_labels(DATA / "labels.csv") == LABELS_SNAPSHOT


def test_validation_labels_are_the_8_figure7_points():
    assert sorted(read_labels(DATA / "val_labels.csv")) == FIGURE7_POINTS


def test_jk_v2_1_matches_paper_v07():
    # The paper quotes "V07 (31.44 wt%)".
    assert round(read_labels(DATA / "val_labels.csv")["JK_V2_1"], 2) == 31.44
