from slip_reader.name_match import best_name_match


# Real plan driver names for the day (correctly spelled).
ROSTER = ["วิโรจน์", "นันทสิทธิ์", "ณัฐวุฒิ", "สันติพงษ์", "ประจัก", "ปกรณ์"]


def test_exact_first_name_matches():
    assert best_name_match("วิโรจน์", ROSTER) == "วิโรจน์"


def test_full_name_matches_first_name_in_roster():
    # OCR gives full name; roster has first name
    assert best_name_match("ปกรณ์ ศรีบุญเรือง", ROSTER) == "ปกรณ์"


def test_fuzzy_corrects_ocr_typo():
    # Haiku misread วิโรจน์ as วิไรจน์ — fuzzy should still land on วิโรจน์
    assert best_name_match("วิไรจน์", ROSTER) == "วิโรจน์"
    assert best_name_match("นิมทสิทธิ์", ROSTER) == "นันทสิทธิ์"


def test_no_match_returns_none_when_too_different():
    assert best_name_match("ใครก็ไม่รู้สักคน", ROSTER) is None


def test_empty_inputs_return_none():
    assert best_name_match("", ROSTER) is None
    assert best_name_match("วิโรจน์", []) is None
