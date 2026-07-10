---
name: project-maint-bill-lines-ocr
description: v49 บันทึกซ่อมคีย์เป็นรายการๆ แยกหมวด (อะไหล่/ค่าแรง/บริการ) + ปุ่ม 📷 อ่านบิลจากรูปด้วย Claude sonnet
metadata: 
  node_type: memory
  type: project
  originSessionId: 3323cfdd-942a-44da-bc85-095450412c8b
---

**โอสั่ง 9 ก.ค. 2026** (ส่งรูปบิลร้านประเสริฐทรัพย์การยาง 28/6/69 รถ 71-8005):
คีย์บิลเป็นรายการๆ + เลือกหมวดต่อบรรทัด และให้ AI อ่านบิลจากรูปกรอกให้

**ทำแล้ว (e4de45b, schema v49, deploy 13:21):**
- `MaintPart.kind` = `part | labor | service` (`models.MAINT_LINE_KINDS`) — ALTER default 'part'
- `_recompute_maint_costs(s, rec, force=())` ใน main.py: parts/labor/other_cost มาจากผลบวก
  บรรทัดแยกหมวด — **หมวดไหนไม่มีบรรทัดเลย คงยอดคีย์มือ ห้ามล้างเป็น 0**;
  ลบบรรทัดสุดท้ายของหมวด → force หมวดนั้นเป็น 0; ค่าแรง/บริการ **ไม่ตัดสต็อก**
- `/maint/records/{id}/read-bill` (upload รูป) → `services/bill_ocr.py` → `claude -p --model sonnet`
  อ่านรูปด้วย Read tool → **ร่าง** แก้ได้ทุกช่อง → กด "➕ เพิ่มเข้าบิล" (`/parts/bulk-add`)
  ถึงเขียน DB; ยอดท้ายบิล ≠ ผลบวกรายการ → เตือน ไม่แก้เงียบ

**gotcha prompt (เจอตอนวัดกับบิลจริง):**
- เขียนว่า "บิลร้านซ่อม/ร้านยาง" → Sonnet **ปฏิเสธบิลปั๊มน้ำมัน** ที่อ่านได้อยู่แล้ว
  → นิยาม `is_bill=false` เฉพาะเมื่อ **ไม่มีรายการราคาเลย**
- Sonnet พ่วงคำอธิบายไทยรอบ JSON → `_extract_json()` อ่านโค้ดบล็อก ```json ก่อน

**สถานะ:** ✅ พิสูจน์กับ**บิลลายมือจริง**ของโอแล้ว (ร้านประเสริฐทรัพย์การยาง 28/6/69) —
4 บรรทัด รวม 4,100 ตรงยอด + ทะเบียน 71-8005 + วันที่ ถูกหมด (ทดสอบในสิทธิ์ SYSTEM)

**🔒 สวิตช์:** `AppSetting bill_ocr_mode` = `admin` (default) | `all` | `off` ตั้งที่หน้า `/ai`
— ปุ่มกินโควต้า Claude Max ของโอ; กันทั้งซ่อนปุ่มและ 403 ที่ route (ไฟล์ไม่ถูกอัปโหลด)

**gotcha ใหญ่:** แอปรันเป็น SYSTEM → claude ต้องมี Git bash (ลงแล้ว) ดู
[[reference-test-claude-as-system]]; route ที่เรียก claude ต้อง `run_in_threadpool` (blocking 40 วิ)

ดู [[reference-claude-cli-reads-images]] · [[project-tire-stop-the-bleed]]

**ต่อยอด 10 ก.ค. (v51 — deploy แล้ว):** 📥 กล่องบิลรอคัด `/maint/bills` — อัปโหลดกองรูป →
worker thread คิว DB (restart-safe, `bill_ocr_mode=off` หยุดคิว) → คัด ➕เข้ารถ /
📦เข้า Stock (ทะเบียนใส่ตอนเบิกออก) / 🗑ทิ้ง; แบ่งเขต: ชีท RM = ของเก่า, กล่องนี้ = บิลใหม่.
บั๊ก 422 ฟอร์มกรอง (`vehicle_id=""` ชน int param) แก้ที่ /maint/records + /maint/inspections
— route ใหม่ที่มี GET filter form ให้รับ str แล้ว `_parse_int` เสมอ.
