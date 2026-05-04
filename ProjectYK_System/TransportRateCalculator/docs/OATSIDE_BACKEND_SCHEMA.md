# Oatside → P&G GPS — Backend Schema (สำหรับโยนให้ Claude บนเว็บ / Artifacts)

**ขอบเขต:** งานลูกค้า **Oatside + P&G (เวลล์โกล)** เท่านั้น — **ไม่**รวม One Platform (`ProjectYK_System/app/`), payroll, daily job  
**ไฟล์โค้ดหลัก (บนเครื่อง):** `Oatside/build_oatside_reports.py`  
**อ่านเต็ม logic:** `ProjectYK_System/TransportRateCalculator/docs/OATSIDE_TRIP_PAIRING_MERGE_HANDOFF.md`

---

## 1) Input / Output

| ทิศทาง | รายการ |
|--------|--------|
| **In** | Excel export GPS 2 ไฟล์: **ต้นทาง** (ชื่อมี `Oatside`) + **ปลายทาง** (`P&G` หรือ `เวลล์โกล`) — ชีตอุปกรณ์ หัวคอลัมน์ไทย แถว detail รูปแบบ `^\d+\.\d+$` ในคอลัมน์แถว |
| **Config** | `Oatside/oatside_config.json` + ไม่บังคับ `Oatside/oatside_billing_overrides.json` (หรือ `OATSIDE_OVERRIDES_JSON`) |
| **Out — Excel** | `Oatside/Oatside_PG_Trip_Summary_By_Site.xlsx` (หลายชีต — ดู §5) |
| **Out — Web static** | โฟลเดอร์รายงาน HTML (slug deploy เช่น `reports/oatside-pg-2026/`): `index.html`, `trips.html`, `plates/<plate>.html` |

**รันบนเครื่อง (ราก repo):** `python Oatside\build_oatside_reports.py`  
**Env บังคับ path:** `OATSIDE_ORIGIN`, `OATSIDE_DEST` — อื่น ๆ ดู §6

---

## 2) โมเดลข้อมูลหลัก (Python dataclass — ชื่อฟิลด์จริงในโค้ด)

### `Leg` (ช่วงเข้า–ออกจุดเดียว ต่อแถวในไฟล์)

| Field | Type | ความหมาย |
|-------|------|-----------|
| `row_no` | str | เลขแถวจากไฟล์ เช่น `10.3` — ใช้จับคู่กับปลายทางรอบแรก |
| `plate` | str | ทะเบียน `71-xxxx` |
| `device` | str | ข้อความอุปกรณ์ |
| `t_in`, `t_out` | datetime | เข้า–ออก geofence |

### `Trip` (หนึ่งเที่ยว matched = ต้นทางรวม + ปลายทางหนึ่งขา)

| Field | ความหมายโดยย่อ |
|-------|------------------|
| `o_in`, `o_out`, `d_in`, `d_out` | เวลาแสดงผล (ต้นอาจมาจากหลาย `Leg` รวมเป็น `o_row` เช่น `10.2+10.3`) |
| `origin_wait_h` | รอที่ต้นทาง — ถ้า merge หลายช่วง = **ผลรวม**ชั่วโมงอยู่ในต้นทางจริง ๆ ไม่นับช่วง “วิ่งนอกต้นทาง” |
| `travel_h` | `Origin_Out` สุดท้าย → `Dest_In` |
| `dest_wait_h` | รอที่ปลายทาง |
| `total_cycle_h` | จากเข้าต้นช่วงแรก → ออกปลายทาง |
| `travel_flag` | หลังคำนวณทั้งชุด — ใช้ IQR ของ `travel_h` ทำเครื่องหมายผิดปกติ (`ABNORMAL`) |

---

## 3) Pipeline ฟังก์ชันหลัก (ลำดับประมาณ)

1. **`parse_legs(path)`** — อ่าน openpyxl, หา worksheet, สร้าง `List[Leg]` เรียง `(plate, t_out)`
2. **`match_plate(origins, dests, max_travel_h)`** — **ปลายทางตามเวลา** → เลือก **ต้นทางที่ `Origin_Out` ล่าสุดก่อน `Dest_In`** ที่ feasible → ได้ `pairs`, `uo`, `ud`
3. **`merge_chained_origin_pairs(pairs, …)`** — รวมหลายช่วงต้นทางก่อนปลายทางเดียว (เปิด/ปิดด้วย config) → `merged_pairs`, `orphan_dests`
4. **`rematch_orphan_dests_to_origins(...)`** — จับคู่ปลายทางค้างกับต้นทางที่เหลือ
5. **`demote_chronology_violations(...)`** — ถ้า `Origin_In` เที่ยวถัดไป `< Dest_Out` เที่ยวก่อน → ย้ายเที่ยวก่อนไป **Unmatched**
6. **สร้าง `Trip`** + คำนวณ billing (เรท + 50% + กฎข้ามคืน / no-work / recovery — ตาม config)
7. **Export Excel** + **HTML** (ตาราง matched ปน unmatched ตามเวลา, การ์ดยอดลูกค้า)

**`feasible(o, d)`:** `d.t_in >= o.t_out` และชั่วโมงระหว่าง ≤ `max_travel_h` (default **48**)

---

## 4) Billing & นโยบาย (สรุปให้ UI ออกแบบตรง field)

| หัวข้อ | พฤติกรรม (อัปเดตถึง พ.ค. 2026 ตามเอกสาร repo) |
|--------|-----------------------------------------------|
| **เรทต่อเที่ยว** | `trip_rate_baht` ตามวันที่ **`Dest_In`**: ช่วง **2026-04-12..15** → **8,000** บาท · **นอกช่วง** → **7,500** |
| **+50% หนึ่งเที่ยว/วัน** | โหมดปฏิทิน: ถ้า `(plate, วัน Dest_In)` มี matched **= 1** → เก็บ **+50%** ของเรทวันนั้น · โหมด **`use_origin_24h_fifty: true`** = หน้าต่าง **24 ชม. rolling จาก `Origin_In`** — ใน window มี 1 เที่ยว → +50%, 2 เที่ยวใน window เดียว → ไม่เก็บ 50% |
| **`charge_min_trip_shortfall`** | default **false** — ไม่เก็บเงินชดเชย “เที่ยวขาดขั้นต่ำ” คู่กับ 50% (ตั้ง true ใน config ถ้าต้องการโหมดเก็บคู่) |
| **`customer_idle_windows`** | ช่วง “ฝากรถลูกค้า / ไม่นับลูกค้า” — ตัด `Dest_Wait` ออกจากการเช็ก 24h และฟิลด์ customer-facing ใน `Trip_Detail` |
| **No-work / recovery / midnight** | มีชีต/คอลัมน์เสริม (`NoWork_Outbound_50pct`, `Nw_outbound50_baht`, fifty ข้ามคืนปลายทาง ฯลฯ) — รายละเอียดใน handoff § เก็บเงิน |

### Overrides JSON (`oatside_billing_overrides.json`)

```json
{
  "version": 1,
  "entries": [
    { "dest_date": "2026-04-14", "plate": "71-6802", "action": "exclude_50", "note": "..." },
    { "dest_date": "2026-04-20", "plate": "71-6001", "action": "include_50", "note": "..." }
  ]
}
```

- **`exclude_50`** — ไม่เก็บ 50% วันนั้นทะเบียนนั้น  
- **`include_50`** — บังคับเก็บ 50% แม้มีมากกว่า 1 เที่ยว

---

## 5) ชีต Excel ที่ควรออกแบบ UI ให้ “สอดคล้อง” (ชื่อหลัก)

| ชีต (ตัวอย่างชื่อ) | ใช้ทำอะไรใน UI |
|--------------------|----------------|
| `Trip_Detail` | รายเที่ยว + เวลา + wait + คอลัมน์ customer cycle / flags |
| `Customer_Summary` | ยอดรวม A/B/C + TOTAL ฝั่งลูกค้า |
| `Customer_Trips_Per_Day` | จำนวนเที่ยว matched รวมต่อวัน (`Dest_In`) + จำนวนรถ — เหมาะกราฟ/heatmap |
| `Plate_DestDay` | รายวันต่อทะเบียน |
| `Surcharge_50pct_1Trip` | รายละเอียดการเก็บ 50% (อาจมี `Window_Origin_In` / `Window_End` เมื่อใช้ origin24h) |
| `Daily_Time_24h_Check` | เช็กชม.รอ/วงจรต่อวัน (หัก customer idle / UM ปลายทางตามนโยบาย) |
| Unmatched / debug ชีตอื่น ๆ | QA, phantom, hints — ดูจาก Excel จริงหลัง build |

---

## 6) ตัวแปรสภาพแวดล้อม (สำหรับ automation / ไม่ใช่ REST API)

| Env | ความหมาย |
|-----|-----------|
| `OATSIDE_ORIGIN` | path ไฟล์ต้นทาง |
| `OATSIDE_DEST` | path ไฟล์ปลายทาง |
| `OATSIDE_MAX_TRAVEL_H` | เพดานชม. ต้น→ปลาย (default 48) |
| `OATSIDE_OVERRIDES_JSON` | path ไฟล์ override แทน `Oatside/oatside_billing_overrides.json` |
| `OATSIDE_LOST_TIME_WAIT_MIN_H` | threshold ชม. รอ (ถ้ายังใช้กับชีต lost-time — ดูค่าในโมดูล) |

**ไม่มี FastAPI endpoint แยก** — งานนี้เป็น **สคริปต์ batch + static HTML**

---

## 7) หน้า HTML ที่มีอยู่ (แนวคิด UI)

- **`index.html`** — สรุปภาพรวม, การ์ด Base / 50% / Total / **grand ลูกค้า**, ลิงก์ไปทะเบียน, ตาราง `Customer_Trips_Per_Day`
- **`trips.html`** — ไทม์ไลน์/ตารางเที่ยวทั้งหมด (matched + UM แทรกตามเวลา)
- **`plates/<plate>.html`** — รายละเอียดรายคัน + “By Dest_In day”

---

## 8) Config flags สำคัญใน `oatside_config.json` (ชื่อที่ใช้ใน repo — อาจขยาย)

สำหรับออกแบบหน้า “ตั้งค่า” หรือ mock: `customer_idle_windows`, `use_origin_24h_fifty`, `enable_origin_chain_merge`, `max_origin_chain_gap_h`, `charge_min_trip_shortfall`, กฎ midnight / full trip / no-work outbound 50% (ดู CHANGELOG 2026-05-01..02 และ handoff)

---

## 9) Prompt ตัวอย่างสำหรับ Claude บนเว็บ (วางคู่กับไฟล์นี้)

> นี่คือ **schema + pipeline** ของระบบรายงาน Oatside→P&G (Python batch, ไม่มี API)  
> ช่วยออกแบบ **Dashboard สมมติ** (Tailwind, modern) ที่มี: (1) สรุปยอดลูกค้าเหมือนการ์ดในรายงาน (2) ตารางรายวัน × ทะเบียนจากแนวคิด `Plate_DestDay` / `Customer_Trips_Per_Day` (3) กราฟจำนวนเที่ยวต่อวัน (4) แถบกรองทะเบียน/ช่วงวันที่  
> ใช้ **ชื่อฟิลด์ในตารางนี้** เป็นหัวคอลัมน์ mock data — ไม่ต้องอ่าน repo จริง

---

*สร้างเป็น “ตัวแทนโครงสร้าง” เพื่อประหยัดโทเค็นและให้ฝั่งเว็บโฟกัส UI — รายละเอียดอัลกอริทึม merge/rematch อ่าน `OATSIDE_TRIP_PAIRING_MERGE_HANDOFF.md`*
