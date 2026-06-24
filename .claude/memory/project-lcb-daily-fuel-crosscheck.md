---
name: project-lcb-daily-fuel-crosscheck
description: Read-only tool flagging LCB daily rows where keyed driver ≠ who reported fueling in Caltex LINE group. Built+tested; data-starved until archiver collects more.
metadata: 
  node_type: memory
  type: project
  originSessionId: 04e0d8eb-194a-4500-bc20-96840fc88ba7
---

ชิ้นแรกของงาน "ข้อมูลขาเข้าเชื่อไม่ได้ → เงินเดือน LCB ผิดทุกเดือน" (โอเลือก attack จุดนี้ก่อน
2026-06-24). เป้า: ลดเวลาที่โอนั่งไล่เทียบเดลี่กับกลุ่มไลน์เองก่อนทำเงินเดือน.

**คืออะไร:** tool อ่านอย่างเดียวที่ `ProjectYK_System/tools/lcb_fuel_crosscheck/`.
parse ข้อความแจ้งเติมน้ำมันจากกลุ่ม LINE "Caltex เพิ่มทรัพย์ข้างศรีไทย" (ใน line_archive.db)
→ เทียบ {ทะเบียน, ชื่อต้นคนขับ, วัน} กับ DailyJob (site=LCB ใน app.db) → ออกรายงาน .md/.html
ที่ reports/. 3 ชนิด finding: driver_mismatch / fueled_no_daily / unparseable.
รัน: `app\.venv\Scripts\python.exe ..\tools\lcb_fuel_crosscheck\run_crosscheck.py <from> <to>`.
**ไม่เขียนอะไรลง DB ไหนเลย.** 19 tests ผ่าน. branch `feat/lcb-daily-fuel-crosscheck` (ยังไม่ merge).

**ดีไซน์/กลยุทธ์ AI (โอย้ำ ใช้ API น้อยสุด):** parser เป็นกติกาฟรี (regex) ไม่เรียก API.
ข้อความที่กติกาจับไม่ได้ → ขึ้น "อ่านไม่ออก ให้คนดู" ไม่เดา. แผนระยะยาว: ใช้ Claude (subscription
ตอนสั่งเป็นรอบ) ช่วยตีความ pattern เพี้ยน แล้ว "ตกผลึกเป็น logic" ฝังใน MVP — API เป็นทางสุดท้าย
จริง ๆ (ต่างจาก slip-reader ที่รูปภาพ จำเป็นต้องใช้ API). spec:
`docs/superpowers/specs/2026-06-24-lcb-daily-fuel-crosscheck-design.md`.

**ข้อเท็จจริงข้อมูล (ยืนยัน 2026-06-24):**
- ข้อความแจ้งเติม pattern ชัด: `<NN-NNNN> นาย<ชื่อต้น> ... ดีเซล/B20 [<NN>L] ... แจ้งเติมCaltex <สาขา>`.
- `DailyJob.driver_raw_name` = ชื่อเต็ม แต่ไลน์ = ชื่อต้น → **จับคู่ด้วยชื่อต้น (token แรก)** ไม่ใช่ทั้ง string.
- ต้องรันชื่อทั้งสองฝั่งผ่าน `app/services/alias_map.py: canonical_person_name(name,"LCB")`
  + `normalize_person_name` ก่อนเทียบ (กัน alias เช่น ณัชพล→ณัชพน ลั่น mismatch ปลอม). reuse ของเดิม.
- ทดสอบจริง 2026-06-12: จับได้ 71-5042 ณัชพล (fueled_no_daily) + 72-1200 (ทะเบียนพิมพ์ผิด น่าจะ 72-1220),
  0 false mismatch บน 5 คันที่ตรงจริง = ตรง hand-trace เป๊ะ.

**ข้อจำกัดใหญ่สุด (บอกโอแล้ว):** archiver เพิ่งเข้ากลุ่ม Caltex → ข้อมูลตื้นมาก.
ทั้งรอบ พ.ค.16–มิ.ย.15 มีข้อความแจ้งเติมแค่ **10 ข้อความ (วันเดียว 2026-06-12)** vs เดลี่ 609 แถว.
tool ถูกต้อง+พร้อม แต่ data-starved — **คุณค่าจะโตเองเมื่อ archiver เก็บข้อความสะสมมากขึ้น**
(ไม่ใช่ปัญหาโค้ด เป็น operational). กลุ่มมีรูป/PDF ปั๊ม 48 รูป (วันเดียวกัน) — ยังไม่อ่าน เก็บรอบหลัง.

**ยังไม่ทำ (รอบถัดไป):** อ่านรูป/PDF ปั๊ม (พจน์ส่ง, ต้อง AI/สายตา), เทียบจำนวนลิตร/ยอดเงิน,
ฝัง logic เข้า MVP เป็นหน้าเว็บ, GPS (โอยืนยัน Claude เข้าไม่ถึง). เกี่ยว:
[[reference-line-archiver]] (แหล่งข้อมูล), [[project-lcb-slip-reader]] (pattern อ่าน→draft→คนอนุมัติ),
[[project-lcb-payroll-may-jun-2026]] (ปลายทางที่ข้อมูลนี้ไปช่วย).
