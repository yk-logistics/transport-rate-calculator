# -*- coding: utf-8 -*-
"""
คำนวณชั่วโมงการทำงานจาก Trip Log
รถ 71-8002 บิ๊กซี ทดสอบวิ่งงาน โฮมโปร
แบ่งเป็น: ชั่วโมงขับรถ | ชั่วโมงรอ/ขึ้นของ/ลงของ
"""

from datetime import datetime, timedelta

def parse_time(day: int, time_str: str) -> datetime:
    """ สร้าง datetime จากวัน (10, 11, 12) และเวลา เช่น '21.00' """
    h, m = map(int, time_str.replace(".", " ").split())
    return datetime(2025, 3, day, h, m)  # ปีสมมติ 2025

def hours_between(start: datetime, end: datetime) -> float:
    """ คำนวณชั่วโมงระหว่างสองเวลา """
    delta = end - start
    return round(delta.total_seconds() / 3600, 2)

def main():
    # ========== กำหนดจุดเวลา (วัน, เวลา) ==========
    # 10 มี.ค.
    t_attach_yard = parse_time(10, "21.00")   # ต่อหาง ลาน YK
    t_rest_stop = parse_time(10, "22.30")     # แวะพัก ปั้ม ปตท.ธัญญะ

    # 11 มี.ค.
    t_depart_ptt = parse_time(11, "03.45")    # ออก ปั้ม ปตท.ธัญญะ
    t_arrive_lg = parse_time(11, "07.30")     # ถึง โรงงาน LG
    t_depart_lg = parse_time(11, "11.30")     # ออก LG (บรรจุเสร็จ)
    t_stop_ptt = parse_time(11, "14.30")      # แวะ ปั้ม (เติมน้ำมัน)
    t_depart_ptt2 = parse_time(11, "15.00")   # ออก ปั้ม
    t_arrive_homepro = parse_time(11, "16.00")  # เข้าคลังโฮมโปร
    t_wait_unload = parse_time(11, "16.30")   # รอลงของ หน้าคลัง 7.2

    # 12 มี.ค.
    t_unload_done = parse_time(12, "11.09")   # ลงของเสร็จ

    # ========== ช่วงที่ถือเป็น "ขับรถ" ==========
    driving_segments = [
        (t_depart_ptt, t_arrive_lg, "ปั้มธัญญะ → โรงงาน LG"),
        (t_depart_lg, t_stop_ptt, "โรงงาน LG → ปั้มธัญญะ"),
        (t_depart_ptt2, t_arrive_homepro, "ปั้มธัญญะ → คลังโฮมโปร"),
    ]

    # ========== ช่วงที่ถือเป็น "รอ/ขึ้นของ/ลงของ" ==========
    wait_segments = [
        (t_arrive_lg, t_depart_lg, "รอขึ้นของที่โรงงาน LG"),
        (t_stop_ptt, t_depart_ptt2, "แวะเติมน้ำมัน ปตท.ธัญญะ"),
        (t_wait_unload, t_unload_done, "รอลงของหน้าคลังโฮมโปร 7.2"),
    ]

    # (ช่วง ต่อหาง + แวะพัก 10/3 21:00–22:30 แล้วพักถึง 03:45 ถือเป็นเตรียมงาน/พัก ไม่นับเป็นชั่วโมงทำงานหลัก หรือจะนับเป็น "งานเตรียม" ก็ได้)
    prep_segment = (t_attach_yard, t_rest_stop, "ต่อหาง + แวะพัก (ลาน YK → ปั้มธัญญะ)")
    rest_overnight = hours_between(t_rest_stop, t_depart_ptt)  # พักกลางคืน

    # ========== คำนวณชั่วโมง ==========
    total_driving = sum(hours_between(s, e) for s, e, _ in driving_segments)
    total_wait = sum(hours_between(s, e) for s, e, _ in wait_segments)
    prep_hours = hours_between(t_attach_yard, t_rest_stop)

    total_work = total_driving + total_wait
    total_work_with_prep = total_work + prep_hours

    # ========== แสดงผล ==========
    print("=" * 60)
    print("สรุปชั่วโมงการทำงาน รถ 71-8002 บิ๊กซี โฮมโปร (10–12 มี.ค.)")
    print("=" * 60)
    print()
    print("【 ชั่วโมงขับรถ 】")
    for start, end, label in driving_segments:
        h = hours_between(start, end)
        print(f"  • {label}: {h:.2f} ชม.")
    print(f"  รวมขับรถ: {total_driving:.2f} ชั่วโมง")
    print()
    print("【 ชั่วโมงรอ / ขึ้นของ–ลงของ 】")
    for start, end, label in wait_segments:
        h = hours_between(start, end)
        print(f"  • {label}: {h:.2f} ชม.")
    print(f"  รวมรอ/ขึ้นของ/ลงของ: {total_wait:.2f} ชั่วโมง")
    print()
    print("【 งานเตรียม (ไม่นับในยอดหลัก) 】")
    print(f"  • {prep_segment[2]}: {prep_hours:.2f} ชม.")
    print(f"  • พักกลางคืน (22:30–03:45): {rest_overnight:.2f} ชม. (ไม่นับเป็นงาน)")
    print()
    print("-" * 60)
    print("รวมชั่วโมงทำงาน (ขับ + รอ/ขึ้นของ/ลงของ):", f"{total_work:.2f} ชั่วโมง")
    print("รวมถ้ารวมงานเตรียม (ต่อหาง+แวะพัก):", f"{total_work_with_prep:.2f} ชั่วโมง")
    print("=" * 60)

if __name__ == "__main__":
    main()
