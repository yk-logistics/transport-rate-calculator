from services.fuel_grade import (
    guess_grade_from_price,
    assign_grades_for_group,
    B20_MAX_HINT,
    GRADE_GAP_MIN,
)


def test_guess_single_price_cheap_is_b20():
    assert guess_grade_from_price(35.2) == "B20"
    assert guess_grade_from_price(36.0) == "B20"


def test_guess_single_price_pricey_is_b7():
    assert guess_grade_from_price(41.2) == "B7"
    assert guess_grade_from_price(40.0) == "B7"


def test_guess_zero_or_negative_is_blank():
    assert guess_grade_from_price(0) == ""
    assert guess_grade_from_price(-5) == ""


def test_group_clear_gap_splits_cheap_b20_pricey_b7():
    # คู่ B7/B20 ในวันเดียว (gap ~6฿) → ถูก=B20 แพง=B7
    assert assign_grades_for_group([41.2, 35.2]) == ["B7", "B20"]
    assert assign_grades_for_group([35.3, 40.8]) == ["B20", "B7"]


def test_group_same_price_both_same_grade():
    # 2 บิลราคาเท่ากัน (เกรดเดียวกัน ไม่ใช่คู่ B7/B20) → absolute fallback ทั้งคู่
    assert assign_grades_for_group([41.2, 41.2]) == ["B7", "B7"]
    assert assign_grades_for_group([35.2, 35.2]) == ["B20", "B20"]


def test_group_single_row_uses_absolute():
    assert assign_grades_for_group([35.2]) == ["B20"]
    assert assign_grades_for_group([41.2]) == ["B7"]


def test_group_three_rows_two_cheap_one_pricey():
    # 27/05 จริง: 35.2, 41.2, 41.2 → B20, B7, B7
    assert assign_grades_for_group([35.2, 41.2, 41.2]) == ["B20", "B7", "B7"]


def test_group_zero_price_stays_blank():
    out = assign_grades_for_group([0.0, 41.2])
    assert out[0] == ""
    assert out[1] == "B7"


def test_constants_present():
    assert B20_MAX_HINT == 38.0
    assert GRADE_GAP_MIN == 3.0
