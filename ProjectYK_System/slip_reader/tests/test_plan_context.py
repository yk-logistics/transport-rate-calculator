from slip_reader.plan_context import parse_plan, plan_lookup

PLAN = """@All **16.06.26** งาน13วิ่ง13
***********************************
KAO2 [DC2]

Job. 26-0914 Agent. YANG MING
รับตู้หนักKERRY [หลังเที่ยงคืน-15.06.26] เปิดคาโอDC อมตะ คืนลานUNIWISE
- นายปกรณ์ ศรีบุญเรือง 063-379-3511
หัว72-1220 หาง72-2952
Con.[40]
"""


def test_parse_plan_extracts_driver_job():
    d = parse_plan(PLAN)
    assert any("ปกรณ์" in k for k in d)
    key = [k for k in d if "ปกรณ์" in k][0]
    entry = d[key][0]
    assert entry["return_yard"] == "UNIWISE"
    assert entry["agent"].startswith("YANG")


def test_plan_lookup_picks_latest_for_day():
    older = ("2026-06-15 16:57", PLAN.replace("UNIWISE", "OLDYARD"))
    newer = ("2026-06-15 22:06", PLAN)
    d = plan_lookup([older, newer], "16.06.26")
    key = [k for k in d if "ปกรณ์" in k][0]
    assert d[key][0]["return_yard"] == "UNIWISE"  # newer wins
