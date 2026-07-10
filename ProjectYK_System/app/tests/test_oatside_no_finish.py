# -*- coding: utf-8 -*-
"""กฎ no_finish 100% ของ engine Oatside — เทียบคำตัดสินจริงของ DHL (IV2606-020, มิ.ย. 2026).

บั๊กที่โอจับได้ 8 ก.ค.: กฎเดิมนับแค่ "0 เที่ยวจบ/วัน + รถแตะต้นทาง ≥1 ชม." ทำให้
วันรอคิว/โหลดของที่ Oatside (ต้นทาง) โดนเก็บ 100% ทั้งที่รถไม่ได้ติดค้างที่ P&G.

กฎใหม่ (ตรงคำตัดสิน DHL ครบทุกแถวที่เขาแก้กลับมา):
1. รถติดค้างปลายทาง (dest leg เดียว ≥8 ชม.ในวันนั้น) → เก็บ 100%   [10/6, 18/6 — DHL จ่าย]
2. ไม่งั้น ถ้าแช่ต้นทาง ≥6 ชม. → ไม่เก็บ (รอคิวโรงงาน)             [9/6, 17/6, 3/6 — DHL ตัด]
3. ไม่งั้น ถ้าแตะต้นทาง ≥1 ชม. + มีเที่ยวจบก่อนหน้าวันนั้น → เก็บ (standby ระหว่างงาน)
                                                                    [12/6, 20/6 — DHL จ่าย]
4. รถใหม่ยังไม่มีเที่ยวแรก → ไม่เก็บ                                 [22/6 รถ 71-8009 — DHL ตัด]

เคสในไฟล์นี้ใช้ timestamp จริงจากไฟล์ DHL คืนกลับ (Downloads/IV2606-020) — อย่าแก้เลขเวลา.
"""
import dataclasses
import importlib.util
import sys
from datetime import date, datetime
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[1] / "oatside" / "build_oatside_reports.py"
_spec = importlib.util.spec_from_file_location("build_oatside_reports_test", ENGINE)
bor = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = bor
_spec.loader.exec_module(bor)


CFG = dataclasses.replace(
    bor._DEFAULT_CONFIG,
    trip_rates=[{"rate_baht": 7000, "base_fuel_min": 31.00, "base_fuel_max": 31.99,
                 "step_pct_per_baht": 1.5}],
    diesel_price_history={date(2026, 6, 1): 31.5},
    one_trip_surcharge_pct_periods=[],
    customer_idle_windows=[],
    customer_no_work_ranges=[],
    outbound_half_dest_dates=frozenset(),
    manual_extra_trips=(),
    manual_return_trips=(),
    report_start_date=date(2026, 6, 1),
    report_end_date=date(2026, 6, 30),
)


def _leg(plate: str, t_in: datetime, t_out: datetime) -> "bor.Leg":
    return bor.Leg(row_no="", plate=plate, device="", t_in=t_in, t_out=t_out)


def _trip(plate: str, o_in: datetime, o_out: datetime, d_in: datetime, d_out: datetime) -> "bor.Trip":
    return bor.Trip(
        plate=plate, site="LCB", device="", o_row="", d_row="",
        o_in=o_in, o_out=o_out, d_in=d_in, d_out=d_out,
        origin_wait_h=(o_out - o_in).total_seconds() / 3600.0,
        travel_h=(d_in - o_out).total_seconds() / 3600.0,
        dest_wait_h=(d_out - d_in).total_seconds() / 3600.0,
        total_cycle_h=(d_out - o_in).total_seconds() / 3600.0,
        origin_date=o_in.date(), dest_date=d_in.date(),
        trip_date=bor._billed_day(o_in, d_out), travel_flag=None,
    )


def _no_finish_days(trips, origin_legs, dest_legs):
    rows, _total = bor.surcharge_billed_day(trips, origin_legs, dest_legs, {}, CFG)
    return sorted(r["dest_date"] for r in rows if r["fifty_kind"] == "no_finish_day")


def test_stuck_at_dest_day_charged_but_origin_evening_day_not():
    """เคสจริง 71-8004 แถว 55: เข้าต้นทางเย็น 9/6 แล้วไปติดค้าง P&G ทั้งวัน 10/6 (destwait 31.3 ชม.)
    engine เดิมเก็บทั้ง 9/6+10/6 (14,720) — DHL ยอมจ่ายวันเดียว → ต้องเก็บเฉพาะ 10/6."""
    plate = "71-8004"
    trips = [_trip(plate,
                   datetime(2026, 6, 9, 17, 40), datetime(2026, 6, 10, 0, 8),
                   datetime(2026, 6, 10, 7, 0), datetime(2026, 6, 11, 14, 30))]  # billed 11/6
    origin_legs = [_leg(plate, datetime(2026, 6, 9, 17, 40), datetime(2026, 6, 10, 0, 8))]
    dest_legs = [_leg(plate, datetime(2026, 6, 10, 7, 0), datetime(2026, 6, 11, 14, 30))]
    assert _no_finish_days(trips, origin_legs, dest_legs) == [date(2026, 6, 10)]


def test_origin_queue_day_not_charged_dest_stuck_day_charged():
    """เคสจริง 71-8004 แถว 82: แช่ต้นทาง 17/6 ทั้งวัน (25 ชม.) แล้วติดค้าง P&G 18/6 (23.1 ชม.)
    engine เดิมเก็บ 17/6+18/6 (14,144) — DHL ตัดวันรอคิวต้นทาง → เก็บเฉพาะ 18/6."""
    plate = "71-8004"
    trips = [_trip(plate,
                   datetime(2026, 6, 17, 6, 9), datetime(2026, 6, 18, 7, 16),
                   datetime(2026, 6, 18, 9, 15), datetime(2026, 6, 19, 8, 27))]  # billed 19/6
    origin_legs = [_leg(plate, datetime(2026, 6, 17, 6, 9), datetime(2026, 6, 18, 7, 16))]
    dest_legs = [_leg(plate, datetime(2026, 6, 18, 9, 15), datetime(2026, 6, 19, 8, 27))]
    assert _no_finish_days(trips, origin_legs, dest_legs) == [date(2026, 6, 18)]


def test_working_day_spanning_midnight_not_charged():
    """เคสจริง 71-5042 แถว 15+20: เที่ยวแรกจบตี 4 (ดึงกลับ billed 2/6) เที่ยวสองออก 3/6 เช้า
    ไปจบ 4/6 เช้า → 3/6 กลายเป็นวัน 0 เที่ยวจบทั้งที่รถทำงานทั้งวัน — DHL ตัดเป็น 0."""
    plate = "71-5042"
    trips = [
        _trip(plate, datetime(2026, 6, 2, 15, 52), datetime(2026, 6, 2, 17, 44),
              datetime(2026, 6, 2, 19, 37), datetime(2026, 6, 3, 3, 59)),   # billed 2/6 (pulled)
        _trip(plate, datetime(2026, 6, 3, 7, 37), datetime(2026, 6, 3, 14, 40),
              datetime(2026, 6, 3, 17, 7), datetime(2026, 6, 4, 7, 8)),     # billed 4/6
    ]
    origin_legs = [
        _leg(plate, datetime(2026, 6, 2, 15, 52), datetime(2026, 6, 2, 17, 44)),
        _leg(plate, datetime(2026, 6, 3, 7, 37), datetime(2026, 6, 3, 14, 40)),
    ]
    dest_legs = [
        _leg(plate, datetime(2026, 6, 2, 19, 37), datetime(2026, 6, 3, 3, 59)),
        _leg(plate, datetime(2026, 6, 3, 17, 7), datetime(2026, 6, 4, 7, 8)),
    ]
    assert _no_finish_days(trips, origin_legs, dest_legs) == []


def test_standby_day_between_trips_still_charged():
    """เคสจริง 71-8004 แถว 57: 12/6 รถว่างรอคำสั่ง (จบเที่ยวก่อน 11/6 บ่าย) เข้าโหลดค่ำ 12/6
    ไปจบ 13/6 → DHL จ่าย 7,264 จริง — กฎใหม่ห้ามตัดวันนี้ทิ้ง (เสียเงินฟรี)."""
    plate = "71-8004"
    trips = [
        _trip(plate, datetime(2026, 6, 9, 17, 40), datetime(2026, 6, 10, 0, 8),
              datetime(2026, 6, 10, 7, 0), datetime(2026, 6, 11, 14, 30)),   # billed 11/6
        _trip(plate, datetime(2026, 6, 12, 19, 42), datetime(2026, 6, 12, 22, 1),
              datetime(2026, 6, 13, 5, 48), datetime(2026, 6, 13, 9, 33)),   # billed 13/6
    ]
    origin_legs = [
        _leg(plate, datetime(2026, 6, 9, 17, 40), datetime(2026, 6, 10, 0, 8)),
        _leg(plate, datetime(2026, 6, 12, 19, 42), datetime(2026, 6, 12, 22, 1)),
    ]
    dest_legs = [
        _leg(plate, datetime(2026, 6, 10, 7, 0), datetime(2026, 6, 11, 14, 30)),
        _leg(plate, datetime(2026, 6, 13, 5, 48), datetime(2026, 6, 13, 9, 33)),
    ]
    days = _no_finish_days(trips, origin_legs, dest_legs)
    assert date(2026, 6, 12) in days


def test_new_truck_first_loading_day_not_charged():
    """เคสจริง 71-8009 แถว 103: รถเข้าประจำการครั้งแรก เข้าต้นทางค่ำ 22/6 (ยังไม่มีเที่ยวจบมาก่อน)
    engine เดิมเก็บ 22/6 (6,976) — DHL ตัดเป็น 0."""
    plate = "71-8009"
    trips = [_trip(plate,
                   datetime(2026, 6, 22, 20, 15), datetime(2026, 6, 23, 16, 59),
                   datetime(2026, 6, 23, 19, 25), datetime(2026, 6, 23, 20, 50))]  # billed 23/6
    origin_legs = [_leg(plate, datetime(2026, 6, 22, 20, 15), datetime(2026, 6, 23, 16, 59))]
    dest_legs = [_leg(plate, datetime(2026, 6, 23, 19, 25), datetime(2026, 6, 23, 20, 50))]
    assert _no_finish_days(trips, origin_legs, dest_legs) == []


def test_audit_rows_agree_with_charges():
    """บรรทัดตรวจทาน (billed_day_audit_rows) ต้องเล่าเหตุผลตรงกับเงินที่เก็บจริง:
    17/6 ไม่เก็บ (รอคิวต้นทาง) / 18/6 เก็บ 100%."""
    plate = "71-8004"
    trips = [_trip(plate,
                   datetime(2026, 6, 17, 6, 9), datetime(2026, 6, 18, 7, 16),
                   datetime(2026, 6, 18, 9, 15), datetime(2026, 6, 19, 8, 27))]
    origin_legs = [_leg(plate, datetime(2026, 6, 17, 6, 9), datetime(2026, 6, 18, 7, 16))]
    dest_legs = [_leg(plate, datetime(2026, 6, 18, 9, 15), datetime(2026, 6, 19, 8, 27))]
    fifty_rows, _ = bor.surcharge_billed_day(trips, origin_legs, dest_legs, {}, CFG)
    audit = bor.billed_day_audit_rows(trips, fifty_rows, origin_legs, dest_legs, {}, CFG)
    by_day = {r["dest_date"]: r for r in audit if r["plate"] == plate}
    assert by_day[date(2026, 6, 18)]["fifty_pct_baht"] == 7000
    assert "100%" in by_day[date(2026, 6, 18)]["billing_note"]
    assert by_day[date(2026, 6, 17)]["fifty_pct_baht"] == 0
    assert "100%" not in by_day[date(2026, 6, 17)]["billing_note"]
