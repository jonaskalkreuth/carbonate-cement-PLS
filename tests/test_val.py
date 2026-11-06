"""Figure-7 point definition: figure7_key and group_specimens."""

from src.val import figure7_key, group_specimens


def test_figure7_key_routes_each_disc():
    assert figure7_key(1, 1) == "JK_V1_1"   # V1-V3 keep their series
    assert figure7_key(3, 2) == "JK_V3_2"
    assert figure7_key(4, 5) == "JK_V4"     # precision discs pool all series
    assert figure7_key(5, 1) == "JK_V5"
    assert figure7_key(6, 1) is None        # below calibration range
    assert figure7_key(7, 1) is None        # optimization sample


def test_group_specimens_on_hand_made_folder(tmp_path):
    for name in ["JK_V1.0", "JK_V1.1", "JK_V1_2.0", "JK_V2_Test.0", ".DS_Store",
                 "JK_V4_1.0", "JK_V4_2.0", "JK_V6_1.0"]:
        (tmp_path / name).touch()

    groups = {k: [p.name for p in ps] for k, ps in group_specimens(tmp_path).items()}

    assert groups == {
        "JK_V1_1": ["JK_V1.0", "JK_V1.1"],     # unnumbered series = series 1
        "JK_V1_2": ["JK_V1_2.0"],
        "JK_V4": ["JK_V4_1.0", "JK_V4_2.0"],   # series pooled; Test, .DS_Store, V6 dropped
    }
