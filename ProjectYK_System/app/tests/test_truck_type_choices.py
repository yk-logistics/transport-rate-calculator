"""Every selectable truck type must have a Thai label and a renderable wheel layout.

Guards the vehicle-edit dropdown: a code the office can pick (TRUCK_TYPES) but
that maps to no tire layout would render an empty tire-check screen.
"""
import models
import main as appmod
import services.tire_view as tv
from models import Vehicle


def test_every_truck_type_has_thai_label():
    for code in models.TRUCK_TYPES:
        assert code in models.TRUCK_TYPE_TH, f"{code} missing Thai label"
        assert models.TRUCK_TYPE_TH[code].strip()


def test_every_truck_type_renders_a_layout():
    for code in models.TRUCK_TYPES:
        v = Vehicle(plate_no="x", truck_type=code)
        pos = appmod._tire_positions_for_vehicle(v)
        assert pos, f"{code} produced no tire positions"
        axles = tv.axle_layout(pos)
        cells = sum(len(a["left"]) + len(a["right"]) for a in axles)
        assert cells == len(pos), f"{code}: {cells} cells != {len(pos)} positions"


def test_every_position_has_thai_label():
    # Lowtech users must never see a raw code like "TRL_L1" on the check screen.
    for code in models.TRUCK_TYPES:
        for pos in appmod._tire_positions_for_vehicle(Vehicle(plate_no="x", truck_type=code)):
            assert pos in models.TIRE_POSITION_TH, f"{pos} ({code}) has no Thai label"


def test_trl8_is_now_selectable_and_is_all_trailer():
    assert "TRL8" in models.TRUCK_TYPES
    pos = appmod._tire_positions_for_vehicle(Vehicle(plate_no="t", truck_type="TRL8"))
    assert all(p.startswith("TRL_") for p in pos)
