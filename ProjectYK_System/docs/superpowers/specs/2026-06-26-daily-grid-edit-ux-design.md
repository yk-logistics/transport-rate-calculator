# /daily grid edit UX: Fullscreen + Undo + Edit-log + กรอกไม่ครบ

วันที่: 2026-06-26
สถานะ: design — โออนุมัติ "ทำทั้งหมด"
ประเภท: ส่วนใหญ่ display/UX; **มี 1 ส่วนแตะ DB** (audit log table) → schema bump

## บริบท (เช็คของจริงแล้ว)

หน้า `/daily` เสิร์ฟ `daily_grid.html` (Tabulator) — **มีอยู่แล้ว**:
- แก้ inline (คอลัมน์ ✎), ปุ่ม "Save Grid" (กดเองถึงบันทึก), dirty-highlight +
  นับ "ยังไม่บันทึก N แถว", เตือนก่อนออกหน้า, filter "ยังกรอกไม่ครบ" (missing=ad/u/any).

โอ **ไม่เคยเห็นฟีเจอร์พวกนี้** → ปัญหาหลัก = discoverability + ขาด Undo/Log/Fullscreen.

บั๊กที่โอกังวล "ตารางเริ่ม 25/5 ไม่ใช่ 16/5" = **ไม่ใช่ข้อมูลหาย** — `/daily` default
`limit=400` เรียงใหม่→เก่า ครอบแค่ ~26/5..15/6. แก้: เพิ่มความชัด/preset.

## สิ่งที่จะทำ (เรียงเล็ก→ใหญ่)

### 1. Fullscreen ตาราง (เล็ก, display)
ปุ่ม "⛶ เต็มจอ" ใน toolbar → ใช้ Fullscreen API (`requestFullscreen()`) บน container
ของ grid. ESC ออก. ไม่มี dependency ใหม่.

### 2. ทำของเดิมให้เห็นชัด (เล็ก, display)
- ปุ่ม "Save Grid" เด่นขึ้น + sticky bar เมื่อมี dirty (แถบลอยล่างจอ
  "ยังไม่บันทึก N แถว · [Save] [ยกเลิกทั้งหมด]")
- ข้อความช่วยเหลือสั้นๆ บนหัวตารางว่าแก้ยังไง

### 3. Undo / Redo การแก้ที่ยังไม่ Save (กลาง, client-only)
- เก็บ stack ของ cell-edits ฝั่ง browser (field, rowId, old, new)
- ปุ่ม "↶ Undo" / "↷ Redo" + คีย์ลัด Ctrl+Z / Ctrl+Shift+Z
- Undo คืนค่า cell เดิม + อัปเดต dirty-map (ถ้ากลับเท่าค่าเดิม → ออกจาก dirty)
- **เฉพาะก่อน Save** (หลัง Save เป็นข้อมูลจริงแล้ว — undo ข้าม Save ไม่ทำ
  รอบนี้; ถ้าพลาดหลัง save ดูจาก Log + แก้ใหม่)

### 4. Edit log: ใครแก้อะไร (กลาง, **แตะ DB**)
- โมเดลใหม่ `DailyJobAudit` (มิเรอร์ `DispatchPlanAudit`):
  id, daily_job_id(idx), changed_at(idx), changed_by, action(edit|create|delete),
  field_name, old_value, new_value
- SCHEMA_VERSION 23→24 + ALTER block (create table)
- `daily_grid_save` (และ daily_save/batch/delete): ก่อนเซ็ตค่าใหม่ ถ้าค่าเปลี่ยน
  เขียน 1 audit row/field, `changed_by = current_user.username`
- หน้าดู log: ปุ่ม "ประวัติ" ต่อแถว → modal/แถบโชว์ audit ล่าสุดของ job นั้น
  (+ หน้า /daily/audit รวมทั้งหมด เรียงเวลา, filter วันที่/คน — phase ย่อย)

### 5. กรอกที่ยังไม่ครบ รวดเดียว (กลาง, ต่อยอด filter เดิม)
- มี preset "🔴 LCB ยังกรอกไม่ครบ" อยู่แล้ว → ทำให้เด่น + เพิ่ม count badge
  (กี่แถวยังว่าง) ดึงจาก total_rows ของ filter missing=any
- โหมด "กรอกเฉพาะช่องว่าง": ปุ่มกระโดด cell ว่างถัดไป (Tab-to-next-empty)
  ในคอลัมน์ ค่าเที่ยว/ค่าขนส่ง เพื่อไล่กรอกเร็ว ไม่ต้องเลื่อนหา

## ลำดับ implement + verify
1. Fullscreen → เปิดหน้า กดปุ่ม เข้า/ออกเต็มจอได้
2. Sticky save bar + ความชัด → render check, ปุ่มโผล่เมื่อ dirty
3. Undo/Redo → แก้ cell, Ctrl+Z คืนค่า, dirty-count ถูก
4. DailyJobAudit + schema 24 → migrate, แก้ 1 ช่อง save แล้วมี audit row + changed_by
5. กรอกไม่ครบ → badge count ตรง, Tab-to-next-empty ทำงาน

## ตรวจย้อนกลับ / ปลอดภัย
- งาน UI ไม่แตะเงิน/payroll. audit เป็น INSERT-only (ไม่แก้ของเดิม)
- schema migrate test บน dev ก่อน; ขึ้น server = copy code + restart (DB server มี
  schema bump auto ตอน lifespan รัน) — ตรวจ schema_version=24 หลัง restart
- backup DB ก่อน migrate (กันพลาด)

## ไม่ทำ (YAGNI)
- Undo ข้าม Save / time-travel ทั้งตาราง
- audit สำหรับทุกตารางในระบบ (เฉพาะ DailyJob รอบนี้)
- เปลี่ยน default limit (แค่ทำให้ preset/ช่วงวันชัด)
