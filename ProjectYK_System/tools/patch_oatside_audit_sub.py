# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parents[2] / "Oatside" / "build_oatside_reports.py"
s = p.read_text(encoding="utf-8")

s = s.replace(
    "    amt = int(fr.get(\"surcharge_baht\", 0) or 0)\n    rate = int(fr.get(\"trip_rate_baht\", 0) or 0)",
    "    amt = int(fr.get(\"surcharge_baht\", 0) or 0)\n    if amt <= 0:\n        return \"\"\n    rate = int(fr.get(\"trip_rate_baht\", 0) or 0)",
    1,
)

s = s.replace(
    "<p class='sub'>เรท: {config_rate_summary(cfg)} ฿/เที่ยว · +{cfg.one_trip_surcharge_pct:.0f}% แสดงเมื่อถูก charge (หลัง override) · Policy:",
    "<p class='sub'>เรท: {config_rate_summary(cfg)} ฿/เที่ยว · คอลัมน์ส่วนเพิ่มแสดงป้ายชัดเจน (ตีเปล่า / ค่าเสียเวลา / ข้ามคืนเต็มเที่ยว +100%) เมื่อมี charge (หลัง override) · Policy:",
    1,
)

s = s.replace(
    "<th>เรท(฿)</th><th>ค่าเที่ยว(฿)</th><th>+{cfg.one_trip_surcharge_pct:.0f}%(฿)</th><th>รวม(฿)</th><th>เหตุผล</th></tr></thead><tbody>",
    "<th>เรท(฿)</th><th>ค่าเที่ยว(฿)</th><th>ส่วนเพิ่ม (฿)</th><th>รวม(฿)</th><th>เหตุผล</th></tr></thead><tbody>",
    1,
)

p.write_text(s, encoding="utf-8")
print("patched audit + zero-amt badge")
