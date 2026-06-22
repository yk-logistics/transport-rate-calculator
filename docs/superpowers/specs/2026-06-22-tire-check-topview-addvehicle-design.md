# ตรวจยาง — Top View + เพิ่มทะเบียนจากลิงก์ — Design Spec

วันที่: 2026-06-22
สถานะ: รอ implementation plan
ต่อยอดจาก: `2026-06-22-tire-inspection-design.md` (magic-link tire check — merged แล้ว)
โมดูล: `ProjectYK_System/app/`

---

## 1. เป้าหมาย

ต่อยอดระบบตรวจยาง magic-link ที่ทำเสร็จแล้ว 2 เรื่อง:
1. **หน้าคนขับเป็น Top View** (ผังรถมองจากบน) แทนรายการเรียงลง — ดูง่าย เห็นภาพรวมทั้งคัน
2. **เพิ่มทะเบียนรถได้จากในลิงก์** — เจอรถที่ยังไม่มีในระบบ เพิ่มเองได้ ไม่ต้องเข้า office

## 2. ขอบเขต

**รวม:**
- เปลี่ยน `check_driver.html` จาก list เป็น Top View layout
- หน้า/ฟอร์มเพิ่มทะเบียนใน flow ลิงก์ (สร้าง `Vehicle` + เลือกประเภท → ตั้งตำแหน่งยางอัตโนมัติ)
- หลัง 2 ข้อนี้เสร็จ → deploy ขึ้นเซิร์ฟเวอร์ (ทำนอก plan นี้ ตามขั้นตอน deploy เดิม)

**ไม่รวม:**
- ไม่แตะ flow ช่าง (queue/measure/job) — คงเดิม
- ไม่แตะ office tire master
- ไม่ทำ OCR ทะเบียน

## 3. เพิ่มทะเบียนจากลิงก์

**Flow:** ในหน้าเลือกรถ (`/check/driver`, `/check/mechanic`) เพิ่มปุ่ม "+ เพิ่มทะเบียนใหม่" ใต้ dropdown → ฟอร์มสั้น:
- ทะเบียน (required)
- ประเภท: ปุ่มเลือก **6 ล้อ / 10 ล้อ / หาง 8 ล้อ** + ช่อง "อื่นๆ" (ระบุ truck_type code เอง เผื่ออนาคต)
- ชื่อเล่น (optional)

กดบันทึก → สร้าง `Vehicle(plate_no, truck_type, vehicle_kind, nickname)` ใน master เดิม → เด้งกลับหน้าตรวจของรถคันนั้น (`?vehicle_id=<new>`)

**Mapping ประเภท → truck_type (ใช้ของเดิมใน `_tire_positions_for_vehicle`):**
| ปุ่มเลือก | truck_type | vehicle_kind | ตำแหน่ง |
|---|---|---|---|
| 6 ล้อ | `6W` | truck/head | 6 ตำแหน่ง |
| 10 ล้อ | `10W` | head | 10 ตำแหน่ง |
| หาง 8 ล้อ | `TRL8` | tail | 8 ตำแหน่ง (`TRL8` map ใหม่ที่ทำไว้แล้ว) |
| อื่นๆ | ค่าที่กรอก | truck | ตาม `_tire_positions_for_vehicle` (fallback 10W) |

**หมายเหตุ:** `_tire_positions_for_vehicle` ปัจจุบัน map `TRL8` ไม่ได้ (มันดู "18/10/6" จาก truck_type) → ต้องเพิ่มเงื่อนไขให้ `TRL8` (และ `tail` + 8) คืน `TIRE_POSITIONS_BY_KIND["TRL8"]`

**Route:** `POST /check/add-vehicle` (public prefix `/check`, gated by token เหมือนหน้าอื่น) — ตรวจ token role อะไรก็เพิ่มได้ (คนขับ/ช่าง). กันทะเบียนซ้ำ (plate_no unique อยู่แล้ว → ถ้าซ้ำ ใช้คันเดิม).

## 4. Top View — หน้าคนขับ

เปลี่ยน `check_driver.html` ส่วนกริดจาก list เป็นผังรถ:
- หัวรถ (cab) + กระดูกงูกลาง = ตัวรถ
- ล้อจัดเป็นแถวต่อเพลา (axle), ซ้าย-ขวาแยกข้าง, นอก/ในเรียงตามตำแหน่งจริง
- แต่ละล้อเป็นปุ่มแตะได้ → เปิด bottom-sheet กรอก (สภาพ + รูป) — sheet เดิม ไม่เปลี่ยน logic
- สีสถานะ: เทา=ยังไม่กรอก, เขียว=กรอกแล้ว, แดง=แจ้งมีปัญหา (อิงค่า `cond_<pos>` ที่เลือก)
- ตัวนับ "x/N เส้น" + ป้ายไทย + จำนวนรูปต่อล้อ (นอก 2 / ใน 1)

**การจัดวางต่อประเภทรถ** (จาก position code):
- 6W: เพลาหน้า (FL|FR) + เพลาหลัง (RLO RLI | RRI RRO)
- 10W: + เพลาหลังตัวที่สอง (RLO2 RLI2 | RRI2 RRO2)
- TRL8: 2 เพลา เพลาละ 4 (LO LI | RI RO)

**Layout เป็น presentation ล้วน** — อ่าน `cells` (มี pos/label/photos/outer + รวมเพลา) จาก handler. เพิ่ม helper จัดกลุ่มตำแหน่งเป็นเพลา+ข้างใน `tire_view.py` (เช่น `axle_layout(positions) -> list[axle]`) เพื่อให้ template วาดผังได้โดยไม่ฝัง logic ใน HTML.

**JS:** สถานะสี + ตัวนับ คำนวณ client-side จาก select ที่เลือก (เหมือน mockup) — minimal vanilla JS, ไม่เพิ่ม library.

## 5. โมเดล/โค้ดที่แตะ

- `services/tire_view.py` — เพิ่ม `axle_layout(positions: tuple) -> list[dict]` (จัดกลุ่มเป็นเพลา → ซ้าย/ขวา → cells) เพื่อให้ Top View วาดง่าย
- `main.py` — `_tire_positions_for_vehicle` รองรับ `TRL8`; route `POST /check/add-vehicle`; ส่ง axle layout เข้า context ของ `/check/driver`
- `templates/check_driver.html` — เขียนกริดใหม่เป็น Top View; เพิ่มปุ่ม+ฟอร์มเพิ่มทะเบียน
- `templates/check_mechanic.html` — เพิ่มปุ่ม+ฟอร์มเพิ่มทะเบียน (เลือกรถ) — optional ถ้า flow ช่างต้องเลือกรถ
- ไม่เพิ่มตาราง/คอลัมน์ใหม่ (`Vehicle` master พอ)

## 6. ความถูกต้อง / กฎข้อมูล

- เพิ่มรถ: กันทะเบียนซ้ำ (unique). ถ้าทะเบียนมีอยู่แล้ว → ใช้คันเดิม ไม่สร้างซ้ำ ไม่ทับ truck_type เดิม (เตือนว่ามีอยู่แล้ว)
- รถที่เพิ่มจากลิงก์ = `source`/notes ระบุว่ามาจาก check-link (เพื่อ audit) — ใช้ field `notes` เดิม
- ไม่กระทบ payroll/billing
- ตำแหน่งยางอิง truck_type — ถ้าเลือกประเภทผิด ตำแหน่งจะผิด → ฟอร์มให้เลือกชัดเป็นปุ่มใหญ่ ไม่ใช่ dropdown เล็ก

## 7. UI มือถือ (คำถามของผู้ใช้: ง่าย/minimal ไหม)

- ตอบได้จริงหลัง **deploy + กดบนมือถือ** — แผนนี้ทำ UI ให้พร้อม แล้ว deploy เพื่อทดสอบนิ้วจริง
- เกณฑ์ minimal: หน้าเดียวจบ, ปุ่มใหญ่แตะง่าย, ไม่ต้องพิมพ์เยอะ (เลือกปุ่ม/แตะล้อ), ไม่ต้อง login

## 8. คำถามที่เหลือสำหรับช่วง plan

- ปุ่มเพิ่มทะเบียนให้โผล่ทั้งคนขับ+ช่าง หรือเฉพาะคนขับ (เริ่ม: ทั้งคู่ เพราะช่างก็เจอรถใหม่)
- "อื่นๆ" ให้กรอก truck_type code ตรงๆ หรือเลือกจาก list ที่มี (`6W/10W/10WL/18W/TRL8`) — เริ่ม: เลือกจาก list
