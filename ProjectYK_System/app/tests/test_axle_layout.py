import services.tire_view as tv
import models


def test_layout_6w_three_cells_per_side_on_rear():
    axles = tv.axle_layout(models.TIRE_POSITIONS_BY_KIND["6W"])
    assert len(axles) == 2                      # front + 1 rear
    front = axles[0]
    assert [c["pos"] for c in front["left"]] == ["FL"]
    assert [c["pos"] for c in front["right"]] == ["FR"]
    rear = axles[1]
    assert [c["pos"] for c in rear["left"]] == ["RLO", "RLI"]   # outer then inner
    assert [c["pos"] for c in rear["right"]] == ["RRI", "RRO"]  # inner then outer
    assert front["left"][0]["label"] == "ซ้ายหน้า"
    assert rear["left"][0]["photos"] == 2 and rear["left"][1]["photos"] == 1


def test_layout_10w_has_front_plus_two_rear():
    axles = tv.axle_layout(models.TIRE_POSITIONS_BY_KIND["10W"])
    assert len(axles) == 3


def test_layout_trl8_two_axles_four_each():
    axles = tv.axle_layout(models.TIRE_POSITIONS_BY_KIND["TRL8"])
    assert len(axles) == 2
    assert sum(len(a["left"]) + len(a["right"]) for a in axles) == 8
