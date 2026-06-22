from datetime import datetime, date
import main as appmod


def test_dmy_hm_shifts_utc_to_thai():
    # stored UTC 12:45 -> Thai 19:45 (+7)
    assert appmod._fmt_dmy_hm(datetime(2026, 6, 22, 12, 45)) == "22/06/2026 19:45"


def test_dmy_hm_rolls_date_near_midnight():
    # UTC 22:30 on the 22nd -> Thai 05:30 on the 23rd
    assert appmod._fmt_dmy_hm(datetime(2026, 6, 22, 22, 30)) == "23/06/2026 05:30"


def test_dmy_hm_iso_string_also_shifts():
    assert appmod._fmt_dmy_hm("2026-06-22T12:45:00") == "22/06/2026 19:45"


def test_dmy_date_only_unchanged():
    # date-only filter has no time, must stay as-is
    assert appmod._fmt_dmy(date(2026, 6, 22)) == "22/06/2026"
