from slip_reader.engine import SlipReadout
from slip_reader.entry_builder import build_entry


def _ro(**o):
    base = dict(is_slip=True, amount=1280.0, recipient_name="ปกรณ์",
                memo="ปกรณ์ คืนตู้", ref_code="REF", slip_time="13:53", direction="out")
    base.update(o)
    return SlipReadout(**base)


PLAN = {"ปกรณ์": [{"job": "26-0914", "agent": "YANG MING",
                  "return_yard": "UNIWISE", "plate_head": "72-1220"}]}


def test_build_basic_payload():
    p = build_entry(_ro(), day="16.06.26", plan=PLAN,
                    slip_line_message_id="618x", slip_media_path="a.jpg")
    assert p["amount"] == 1280.0 and p["site_code"] == "LCB"
    assert p["slip_line_message_id"] == "618x"
    assert p["requester_raw"] == "ปกรณ์"
    assert p["txn_date"] == "2026-06-16"


def test_plan_enriches_memo_and_confidence():
    p = build_entry(_ro(), day="16.06.26", plan=PLAN,
                    slip_line_message_id="618y", slip_media_path="")
    assert "UNIWISE" in p["memo"] and p["parsed_confidence"] == 0.9


def test_no_plan_match_lower_confidence():
    p = build_entry(_ro(recipient_name="ใครก็ไม่รู้สักคน", memo="คืนตู้"),
                    day="16.06.26", plan=PLAN, slip_line_message_id="z", slip_media_path="")
    assert p["parsed_confidence"] == 0.6


def test_fuzzy_corrects_ocr_misread_name_from_plan():
    # OCR misread ปกรณ์ as ปกรน์ — plan roster corrects requester_raw to ปกรณ์
    p = build_entry(_ro(recipient_name="ปกรน์ ศรีบุญเรือง"),
                    day="16.06.26", plan=PLAN, slip_line_message_id="f", slip_media_path="")
    assert p["requester_raw"] == "ปกรณ์" and p["parsed_confidence"] == 0.9


def test_advance_category_from_memo():
    p = build_entry(_ro(memo="ประจัก เบิก"), day="16.06.26", plan=PLAN,
                    slip_line_message_id="w", slip_media_path="")
    assert p["category"] == "driver_advance"


def test_non_slip_returns_none():
    assert build_entry(_ro(is_slip=False), day="16.06.26", plan={},
                       slip_line_message_id="q", slip_media_path="") is None


def test_no_amount_returns_none():
    assert build_entry(_ro(amount=None), day="16.06.26", plan={},
                       slip_line_message_id="q", slip_media_path="") is None
