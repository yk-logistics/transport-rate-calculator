# -*- coding: utf-8 -*-
"""เพิ่ม BH/ตีเปล่า เข้า oatside_config.json (แก้รอบ scrutinize: amount_baht ระบุตรง + ปรับ 8001/8005).
   idempotent — ลบ entry พ.ค. ของ 7 คันก่อน แล้วใส่ชุดที่ถูกต้อง (72-1217 เม.ย. ไม่แตะ)."""
import json
from pathlib import Path

CFG = Path(__file__).with_name("oatside_config.json")
MINE = {"71-5041","71-5042","71-6802","71-8001","71-8002","71-8005","71-8009"}

BH = "BH ขากลับ P&G>บ้านบึง 50%"
EM = "ตีเปล่าไป P&G 50%"
# plate, dest_date, amount_baht, note
ENTRIES = [
    ("71-5042", "2026-05-01", 3632, EM),
    ("71-8009", "2026-05-10", 3584, BH),
    ("71-8009", "2026-05-11", 3584, BH),
    ("71-8002", "2026-05-20", 3728, BH),
    ("71-8009", "2026-05-20", 3728, BH),
    ("71-8001", "2026-05-20", 3728, "BH ขากลับเพิ่ม 50% (base คิด ตีเปล่า+BH#1 = 1 เที่ยวแล้ว)"),
    ("71-8001", "2026-05-21", 3728, BH),
    ("71-8009", "2026-05-22", 3728, BH),
]

d = json.load(open(CFG, encoding="utf-8"))
lst = d.get("manual_return_trips", [])
# ลบของเดิม (พ.ค. ของ 7 คัน) เพื่อ replace
lst = [e for e in lst if not (e.get("plate") in MINE and str(e.get("dest_date", "")).startswith("2026-05"))]
for plate, date, amt, note in ENTRIES:
    lst.append({"dest_date": date, "plate": plate, "amount_baht": amt, "note": note})
d["manual_return_trips"] = lst
json.dump(d, open(CFG, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
total = sum(e["amount_baht"] for e in lst if e.get("plate") in MINE)
print(f"entries (7 คัน พ.ค.) = {len([e for e in lst if e.get('plate') in MINE])} · รวม = {total:,} บาท · total list = {len(lst)}")
