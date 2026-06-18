# LCB Slip-Reader → Review-in-MVP (เฟสถัดไป)

วันที่: 2026-06-18
สถานะ: design approved → writing plan
เจ้าของโดเมน: โอ (พงษกาญจน์)
ต่อยอดจาก: `2026-06-18-lcb-petty-ai-accuracy-proof-design.md` (proof ผ่านแล้ว — OCR สลิป 100%)

---

## 1. เป้าหมาย

แก้ pain หลักของโอ: *"โอนเงินเสร็จต้องมานั่งลงชีต"*.
ให้ AI อ่านสลิปโอนจากกลุ่ม LINE LCB → ร่างรายการสดย่อย (คน/ยอด/งาน) → **หมิว/แอดมิน
กดอนุมัติในหน้าเว็บ MVP** → ลงเป็น petty entry จริงใน MVP DB.

**ขอบเขตเฟสนี้ (ตามที่โอเลือก):**
- ไซท์: **LCB ที่เดียว**
- ปลายทาง: **MVP DB เท่านั้น** — ✋ ยังไม่เขียน Google Sheet (เขาใช้ชีตจริงอยู่;
  รอระบบนิ่งค่อยทำ sync ชีตทีหลัง)
- คนอนุมัติ: หมิว/แอดมิน **login หน้าเว็บ MVP** (RBAC มีแล้ว)
- engine อ่านสลิป: **สลับได้**, ตั้ง **Claude API (Haiku)** ไว้ก่อน
- รันที่: **server รวมกับ archiver**

## 2. หลักการสถาปัตยกรรม (2 จุดที่โอเห็นด้วยแล้ว)

**(A) slip-reader เป็น service ใหม่ แยกขาด** — ไม่แก้โค้ด archiver เดิม. แค่ **อ่าน**
`line_archive.db` (ที่ archiver เขียน) แบบ read-only + เขียนผลเข้า MVP DB ผ่าน API.
ถ้า slip-reader พัง → archiver กับ MVP ยังรอดทั้งคู่. (เหมือน archiver แยกจาก MVP วันนี้.)

**(B) สลิปไม่เข้าเป็น entry จริงตรง ๆ — ผ่าน "สถานะรอ"** — กฎเงิน (AI เสนอ คนยืนยัน)
ฝังในสถาปัตยกรรม ไม่ใช่แค่สัญญา.

## 3. โมเดลข้อมูล (surgical — ใช้ของเดิมเป็นหลัก)

ตรวจแล้ว: `PettyCashTxn` (models.py:218) **มีฟิลด์รองรับเกือบครบ**:
`status`, `source`, `parsed_confidence`, `parsed_payload_json`, `category`, `direction`,
`driver_id`, `requester_raw`, `amount`, `memo`, `has_receipt`, `deduct_from_driver`.

→ **ไม่สร้างตารางใหม่.** "รายการรออนุมัติ" = `PettyCashTxn` ที่:
- `status = "pending_review"` (เพิ่มค่าใหม่ใน `PETTY_TXN_STATUS`)
- `source = "line_slip"`
- `parsed_confidence` = ความมั่นใจ AI, `parsed_payload_json` = ผลดิบที่ AI อ่าน

**เพิ่มฟิลด์ใหม่เท่าที่จำเป็น** (provenance — ย้อนกลับไปดูสลิปต้นทางได้):
- `slip_line_message_id: str = ""` — id ข้อความ LINE ของสลิป (กันอ่านซ้ำ — idempotent)
- `slip_media_path: str = ""` — path รูปสลิปใน archiver
- `slip_ref_code: str = ""` — รหัสอ้างอิงสลิป (กันโอนซ้ำ/ตรวจย้อน)

เพิ่ม `SCHEMA_VERSION` 19 → 20 + ALTER TABLE block ใน `lifespan()` (3 คอลัมน์ใหม่ TEXT
default '') ตาม pattern เดิม.

เพิ่ม `("pending_review", "รอ AI อ่าน—รออนุมัติ")` ใน `PETTY_TXN_STATUS`.

## 4. หน่วยย่อย (แต่ละชิ้นทำงานเดียว เทสต์แยกได้)

### บน server (slip-reader service ใหม่, โฟลเดอร์แยก)
| หน่วย | หน้าที่ | depends |
|------|--------|---------|
| `slip_source` | อ่าน archive: ดึงสลิปฝั่งบริษัทกลุ่ม LCB ที่ยังไม่ประมวลผล (by message_id) | line_archive.db (RO) |
| `slip_classifier` | คัด: รูปนี้เป็นสลิปโอนไหม (vs ใบงาน/แพลน/ตารางสรุป) | engine |
| `slip_ocr` | อ่านสลิป → {amount, recipient_name, memo, ref_code, time, direction} | **engine (สลับได้)** |
| `plan_context` | อ่านแพลนงานล่าสุดของวันนั้น (รวมที่แก้ไข) → lookup "วันนี้ใครวิ่งงานอะไร/คืนลานไหน/ลูกค้า" | line_archive.db (RO) |
| `entry_builder` | ประกอบ PettyCashTxn draft (map ชื่อ→driver_id, งาน→category, confidence) + ใช้ plan_context เติม note/ยืนยันคน/ตีธงถ้าไม่ตรง | alias_map, plan_context |
| `mvp_push` | POST รายการเข้า MVP ผ่าน endpoint ใหม่ (idempotent by slip_line_message_id) | MVP API |

### plan_context — ตัวช่วย ไม่ใช่ระบบแพลนเต็ม (กัน scope บวม)

แพลนในกลุ่มมีโครงสร้างชัด (หัวหน้า KhaoFang/Mark แจ้งทุกวัน; แก้ไขแจ้งกลุ่มเดิม):
```
**16.06.26** ...
Job. 26-0914  Agent. YANG MING
รับตู้หนักKERRY ... คืนลานUNIWISE
- นายปกรณ์ ศรีบุญเรือง   หัว72-1220 หาง72-2952
```
- parse แพลน text ของวัน → dict: `{driver_name: [{job, customer, return_yard, plate, date}]}`
- ถ้ามีหลายเวอร์ชัน (แก้ไข) → **ใช้อันล่าสุด** ที่ระบุวันเดียวกัน
- ป้อนให้ `entry_builder`: (1) เติม `memo`/note แบบที่ชีตใช้ (เช่น "KLND CNC 17/6/26");
  (2) ถ้าแท็กกำกวม ใช้แพลนยืนยันคน; (3) ถ้าสลิป-คน ไม่อยู่ในแพลนวันนั้น → ตีธง confidence ต่ำ
- **ทำเฉพาะ best-effort** — แพลน parse ไม่ได้/ไม่เจอ ไม่บล็อก (สลิปยังสร้าง draft ได้ตามปกติ)
- ❌ ไม่สร้างตารางแพลน ไม่มีหน้าจัดการแพลน (นั่นคืออนาคต "แบบ C")

### engine interface (สลับได้ — กุญแจของ "สลับ Claude↔Qwen")
```
class SlipEngine(Protocol):
    def is_slip(self, image_bytes) -> bool          # ใช่สลิปโอนไหม
    def read_slip(self, image_bytes) -> SlipReadout  # amount/name/memo/ref/time
```
- `ClaudeSlipEngine` (Anthropic API, Haiku) — ตั้งไว้ default
- (เผื่ออนาคต) `QwenSlipEngine` — implement interface เดียวกัน, สลับด้วย env/config
- เลือก engine จาก config ค่าเดียว (`SLIP_ENGINE=claude|qwen`). ไม่แตะหน่วยอื่น.

### ใน MVP (app/)
| หน่วย | หน้าที่ |
|------|--------|
| `POST /api/petty/ingest` | รับ draft จาก slip-reader → สร้าง `PettyCashTxn(status=pending_review)`; idempotent by `slip_line_message_id` (มีแล้ว = skip). auth = service token. |
| `GET /petty/review` | หน้าเว็บ: list รายการ `pending_review` ของ LCB เรียงตามเวลา; แสดง คน/ยอด/งาน/confidence + ลิงก์รูปสลิป. หมิว/แอดมิน login. |
| `POST /petty/review/{id}/approve` | เปลี่ยน `pending_review` → `posted` (เป็น entry จริง). แก้ field ได้ก่อนอนุมัติ. |
| `POST /petty/review/{id}/reject` | ทิ้ง (status=`draft` หรือลบ — ไม่กระทบยอดจริง). |

## 5. Data flow (idempotent — รันซ้ำไม่เกิดรายการซ้ำ)

```
archiver → line_archive.db
slip-reader (รอบ ๆ / cron บน server):
  1. slip_source: หา company image กลุ่ม LCB ที่ slip_line_message_id ยังไม่เคยส่ง
  2. slip_classifier: ใช่สลิปไหม → ไม่ใช่ ข้าม (log)
  3. slip_ocr (engine): อ่านยอด/ชื่อ/memo/ref/time
  3b. plan_context: โหลดแพลนของวันนั้น (best-effort)
  4. entry_builder: map + เติม note/ยืนยันคนจากแพลน → draft + confidence
  5. mvp_push → POST /api/petty/ingest (idempotent)
MVP:
  6. /petty/review : หมิวเห็น draft → อนุมัติ/แก้/ทิ้ง
  7. approve → posted (เข้า petty จริง LCB)
```

กันซ้ำ 2 ชั้น: (1) slip_source จำ message_id ที่ส่งแล้ว (2) ingest endpoint unique by
`slip_line_message_id`.

## 6. Error handling

- engine อ่านไม่ออก/ไม่มียอด → **ไม่สร้าง draft** (ตี log "unreadable"), ไม่เดายอด.
- ชื่อ map ไม่เจอ driver → สร้าง draft แต่ `driver_id=None`, confidence ต่ำ,
  หน้า review บังคับให้คนเลือกคนก่อนอนุมัติ.
- slip-reader ล่ม / API ล่ม → archiver & MVP ไม่กระทบ; ครั้งถัดไปไล่ message_id ต่อ
  (idempotent ทำให้รันซ้ำได้ปลอดภัย).
- ห้าม auto-approve. ทุก entry จริงต้องผ่านปุ่มคน.

## 7. กฎเงิน (ฝังในดีไซน์)

- ✅ ยอดมาจากสลิปเท่านั้น (พิสูจน์แล้ว 100%); อ่านไม่ได้ = ไม่สร้าง
- ✅ ทุกรายการผ่าน `pending_review` → คนกด approve เสมอ (ไม่มี auto-post)
- ✅ idempotent by slip message id — กันลงซ้ำ (บทเรียน [[feedback-test-data-cleanup-safety]])
- ✅ LCB เท่านั้นเฟสนี้ — site_code ติดทุก row, ไม่ปนไซท์
- ✅ ยังไม่แตะ Google Sheet — ไม่กระทบงานจริงที่หมิวทำอยู่

## 8. ทดสอบ / preflight

- unit: `slip_ocr` กับสลิปตัวอย่างที่ proof เก็บไว้ (รู้เฉลยแล้ว) → ต้องได้ยอด/ชื่อตรง
- unit: `entry_builder` map ชื่อ→driver, งาน→category (alias_map)
- idempotent: ยิง ingest ซ้ำ message เดิม → ไม่เกิด row ใหม่
- หน้า review: approve แล้ว row เปลี่ยน posted + โผล่ในยอด petty LCB; reject ไม่กระทบยอด
- ตรวจย้อน: ทุก posted entry มี slip_media_path + ref_code ชี้กลับสลิปต้นทางได้

## 9. ไม่ทำในเฟสนี้ (YAGNI)

- ❌ เขียน Google Sheet (เฟสหลัง เมื่อระบบนิ่ง)
- ❌ ไซท์อื่น (วังน้อย/BigC) — LCB ก่อน
- ❌ คำนวณเงินทอน→หักเบิกรายสัปดาห์อัตโนมัติ (เฟสถัดไปอีกที — มีฐานจาก petty ที่อนุมัติแล้ว)
- ❌ จับคู่กับแพลนงาน (อนาคต C — ต้องมีหน้าแพลนก่อน)
- ❌ realtime/ดูทุกข้อความ — รันเป็นรอบพอ (แม่นเท่ากัน ถูกกว่า; ดู [[project-ai-watch-line-group]])
