from models import Vehicle
import main as appmod


def test_trl8_returns_eight_trailer_positions():
    v = Vehicle(plate_no="T-1", truck_type="TRL8", vehicle_kind="tail")
    pos = appmod._tire_positions_for_vehicle(v)
    assert len(pos) == 8
    assert pos[0] == "TRL_LO1"
    assert pos[-1] == "TRL_RO2"


def test_six_and_ten_still_work():
    assert len(appmod._tire_positions_for_vehicle(Vehicle(plate_no="a", truck_type="6W"))) == 6
    assert len(appmod._tire_positions_for_vehicle(Vehicle(plate_no="b", truck_type="10W"))) == 10
