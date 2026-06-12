# LINE archiver — จัดหมวด Discord อัตโนมัติ

วันที่: 2026-06-12
ขอบเขต: `ProjectYK_System/line_archiver/` (service แยก port 8020 — ไม่แตะ app MVP)
ที่มา: TODO เฟสถัดไป ข้อ 1 ใน `reference-line-archiver` memory

## ปัญหา

ตอนนี้ทุก channel ที่บอท auto-create อยู่ที่ root ของ Discord guild ปนกัน 45+ channel
หากลุ่มยาก โออยากให้ archiver จัด channel เข้า **category** อัตโนมัติตามชื่อกลุ่ม
และจัดย้อนหลังกลุ่มเดิมทั้งหมด

## Category scheme (5 หมวด)

จับจากชื่อกลุ่มจริง 45 กลุ่ม + โอยืนยัน. ตรวจ **ตามลำดับ** (เจอตัวแรกหยุด):

| # | Category | คีย์เวิร์ด (ในชื่อกลุ่ม, lowercase) |
|---|----------|-------------------------------------|
| 1 | ลูกค้า-DHL | `dhl`, `เรียกรถ` (Chevrolet เป็นงาน DHL) |
| 2 | ซ่อมบำรุง | `ซ่อม`, `อู่`, `อู๋`, `ช่าง`, `ยาง`, `ไทร์`, `tire`, `isuzu`, `ออโต้`, `เทคนิค`, `การยาง`, `p&w`, `superpart`, `spp` |
| 3 | น้ำมัน | `caltex`, `ปตท`, `ptt`, `น้ำมัน`, `เชื้อเพลิง` |
| 4 | ภายใน | `บัญชี`, `สำนักงาน`, `test`, `วาย.เค.ลอจิสติค`, `หัวลาก`, `พขร`, `หัวหน้างาน`, `ขับรถ` |
| 5 | ลูกค้า-อื่นๆ | *(default — ไม่เข้าข้อ 1-4)* |

### Override พิเศษ (exact match ก่อนเข้า keyword loop)
- `Fleet YK` → **ลูกค้า-อื่นๆ** (จริงๆ คือ Homepro ไม่ใช่ fleet ภายใน — กัน keyword `fleet` พาผิด; ไม่มี keyword fleet อยู่แล้วจึง default พอ แต่ระบุไว้กันสับสน)

### เหตุผลลำดับ (edge cases ที่ลำดับสำคัญ)
- DHL ก่อนทุกอย่าง: "SUB YK & DHL BPD" มี DHL → ต้องลง DHL
- ซ่อมก่อนลูกค้า: "Y.K.ลอจิสติค&อู่เล็ก" มี "อู่" → ซ่อม ไม่ใช่ลูกค้า
- "P&W" / "Y.K. logistics/P&W" → ทั้งคู่ซ่อม (ร้านอะไหล่)
- "เรียกรถ YK Logistic" → DHL (Chevrolet)

## โครงสร้างโค้ด

### ไฟล์ใหม่ `categories.py`
- `CATEGORY_RULES`: `list[tuple[str, list[str]]]` — (category_name, keywords) เรียงตามลำดับตรวจ
- `EXACT_OVERRIDES`: `dict[str, str]` — ชื่อกลุ่มตรงเป๊ะ → category (normalize lower+strip)
- `category_for(group_name: str | None) -> str` — pure function:
  1. ถ้าชื่อ (normalized) อยู่ใน EXACT_OVERRIDES → คืนค่านั้น
  2. ไล่ CATEGORY_RULES ตามลำดับ; keyword ตัวใดอยู่ใน lower(name) → คืน category
  3. ไม่เจอ → "ลูกค้า-อื่นๆ"

### `discord_api.py` — เพิ่ม 3 method ใน DiscordClient
- `list_channels() -> list[dict]` — GET `/guilds/{guild}/channels`
- `ensure_category(name: str) -> str` — หา channel type=4 ชื่อตรง (ผ่าน list_channels) ถ้าไม่มี POST สร้าง (type=4). cache `{name: id}` ใน instance ลด API call
- `move_channel(channel_id: str, parent_id: str) -> None` — PATCH `/channels/{id}` body `{"parent_id": parent_id}`

### `db.py` — เพิ่มคอลัมน์ category
- `connect()`: idempotent `ALTER TABLE line_group ADD COLUMN category TEXT` (try/except OperationalError — column exists)
- `set_group_category(conn, group_id, category)` setter

### `archiver.py` — ผูก category ตอน create channel
- ใน `_ensure_channel`: หลัง `create_channel` สำเร็จ → คำนวณ `category_for(name)`, `ensure_category`, `move_channel`, `set_group_category`.
- best-effort: ครอบ try/except, fail → log แล้วผ่าน (channel อยู่ root, ข้อความยัง forward — ข้อมูลไม่หาย เหมือน forward retry)
- **move-only ไม่ pin**: ทำเฉพาะตอน create ครั้งแรก (channel_id ยังว่าง) — ถ้าโอย้าย channel เองทีหลัง archiver ไม่ดึงกลับ

### Backfill `tools/backfill_categories.py` (ใน line_archiver/)
- `--dry-run` (default): อ่าน line_group ทุกแถวที่มี discord_channel_id → พิมพ์ตาราง `ชื่อกลุ่ม → category` ลงไฟล์ UTF-8 (`backfill_preview.txt`) + console สรุปนับต่อหมวด. **ไม่แตะ Discord**
- `--apply`: ensure 5 categories, move ทุก channel เข้า parent ตาม category_for, เขียน category ลง DB. respect 429 retry_after.

## Error handling
- จัด category พลาด (Discord error) → log + ผ่าน; channel ยังอยู่ root, forward ยังทำงาน
- Backfill `--apply` เจอ 429 → sleep `retry_after` แล้ว retry แถวเดิม

## Testing
- `tests/test_categories.py`: assert ทุกกลุ่มจริง 45 กลุ่ม → category ถูก (โดยเฉพาะ edge: อู่เล็ก→ซ่อม, DHL BPD→DHL, P&W→ซ่อม, เรียกรถ→DHL, Fleet→ลูกค้า-อื่นๆ, default→ลูกค้า-อื่นๆ)
- `tests/test_discord_api.py`: ensure_category cache (สร้างครั้งเดียวเมื่อชื่อซ้ำ), move_channel ส่ง parent_id ถูก — ผ่าน fake httpx/transport
- `tests/test_archiver.py`: เพิ่มเคส create channel → category ถูกผูก (FakeDiscord เก็บ moves[]); Discord category fail → channel ยัง forward ได้
- รัน backfill `--dry-run` จริงกับ DB จริง → โอรีวิวตาราง 45 กลุ่มก่อน apply

## ลำดับงาน
1. categories.py + test (pure, ไม่แตะเน็ต)
2. db.py column + setter
3. discord_api.py 3 method + test
4. archiver.py ผูก category + test
5. backfill script
6. รัน dry-run จริง → โอรีวิว → apply
