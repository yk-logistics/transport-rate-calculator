# Oatside — chain-merge ต้นทาง (Origin): บั๊ก gap + โหมดปิดรวบทั้งหมด

## โหมดแนะนำ (2026-05-01 อัปเดต): **ไม่รวบ Origin เลย**

ตั้งใน **`Oatside/oatside_config.json`**:

```json
"enable_origin_chain_merge": false
```

- **`false` (ค่าเริ่มต้นในโค้ด)** = ไม่เรียก `merge_chained_origin_pairs` — แต่ละคู่จาก `match_plate` คงไว้ตามนั้น (ไม่รวมหลายแถวต้นทางก่อนปลายทางเที่ยวเดียว)
- **`true`** = เปิดการรวบแบบเดิม โดยใช้ **`max_origin_chain_gap_h`** (ชม.) เป็นเกณฑ์หยุดเมื่อช่องว่าง `Origin_Out` → `Origin_In` ถัดไปยาวเกินกำหนด

ใน Excel Info sheet จะมีบรรทัด **`Enable_origin_chain_merge: True/False`**

### Build ด้วยไฟล์ GPS ที่ระบุชื่อเอง (PowerShell)

จากรากโปรเจกต์ (แก้ path ให้ตรงเครื่อง):

```powershell
$env:OATSIDE_ORIGIN = "C:\Users\Home\Desktop\Project YK\Oatside\Y.K._Logistics_Solutions_Service_Co.,_Ltd._รายงานการผ่านจุด_02.05.2026_06-56-46 Oatside.xlsx"
$env:OATSIDE_DEST  = "C:\Users\Home\Desktop\Project YK\Oatside\Y.K._Logistics_Solutions_Service_Co.,_Ltd._รายงานการผ่านจุด_02.05.2026_06-58-42 P&G.xlsx"
python Oatside\build_oatside_reports.py
```

หรือรันสคริปต์ตัวอย่าง: `python ProjectYK_System\tools\run_oatside_may02_build.py` (อัปเดตชื่อไฟล์ในไฟล์สคริปต์ให้ตรง export ล่าสุด)

**ทำไมบางคู่ “ดูแล้วควร match” แต่กลายเป็น UM:** อ่าน **`TransportRateCalculator/docs/OATSIDE_TRIP_PAIRING_MERGE_HANDOFF.md`** หัวข้อกรณี 71-6802 — สรุปสั้นๆ คือ **greedy `match_plate` + `demote_chronology_violations`** ไม่ใช่แค่ช่องว่างชั่วโมงระหว่าง `Origin_Out` กับ `Dest_In`

**ผล build ล่าสุดที่บันทึกไว้ (ชุด 02.05.2026 — Origin `07-15-32` + Dest `06-58-42`, merge ปิด, `match_plate` แบบปลายทางก่อน):** Trips **105** | Unmatched legs **15** — ตัวเลขจะเปลี่ยนตาม export ใหม่

---

## อาการที่พบ (เมื่อเปิด merge แบบเก่า)

- ใน Excel มี **สองแถวต้นทาง** ติดกันของคันเดียวกัน เช่น  
  - แถว 64: เข้า `11:50` — ออก `14:54`  
  - แถว 65: เข้า `19:26` — ออก `01:01` (วันถัดไป)
- แต่ในรายงาน HTML กลายเป็น **Origin In จากแถว 64** ไปจับกับ **Origin Out จากแถว 65** (ออกตี 1) — **ข้ามช่วงที่รถกลับฮับ/พักจริง**

## สาเหตุ (โค้ด)

ฟังก์ชัน **`merge_chained_origin_pairs`** ออกแบบมาเพื่อกรณี “double origin” ก่อนปลายทางเที่ยวเดียว: ถ้า **Origin ถัดไปเข้าก่อน `Dest_In` ของเที่ยวปัจจุบัน** (`o2.t_in < d_acc.t_in`) จะ **รวมช่วง Origin** เป็น `t_in` ช่วงแรก + `t_out` ช่วงหลัง

ข้อบกพร่อง: ถ้า **ปลายทาง (`Dest_In`) มาช้ามาก** (เช้าวันถัดไป) เงื่อนไข `o2.t_in < d_acc.t_in` ยังเป็นจริงได้แม้คนขับ **กลับฮับแล้วออกรอบใหม่หลายชั่วโมง** — ระบบจึงยัง “เห็น” ว่าเป็น chain เดียวกันและรวม `Origin_Out` ผิด

## การแก้ (2026-05-01)

เพิ่มเกณฑ์ **ช่องว่างสูงสุด (ชม.)** ระหว่าง **`Origin_Out` ของช่วงที่สะสมอยู่** กับ **`Origin_In` ของช่วงถัดไป**:

- ถ้า `hours(o_acc.t_out, o2.t_in) > max_origin_chain_gap_h` → **ไม่รวม** — ถือว่าเป็น **รอบเข้าฮับใหม่**
- ค่าเริ่มต้นในโค้ด / `oatside_config.json` template: **`max_origin_chain_gap_h`: 3** (ชม.)

ปรับได้ใน **`Oatside/oatside_config.json`** โดยไม่ต้องแก้โค้ด (ถ้าโหมด hub ของคุณต้องยอมรับช่องว่างยาวกว่า 3 ชม. จริงๆ ค่อยเพิ่มทีละน้อยแล้วรัน build ทดสอบ)

## ผลกระทบที่ต้องรู้

- หลังปิดการรวมแบบผิดๆ จำนวน **matched trips / unmatched legs** อาจเปลี่ยน (มักเห็น **unmatched เพิ่ม** ชั่วคราว) — ควรเทียบกับ Excel รอบเดียวกันแล้วตัดสินใจว่าต้องปรับ `max_origin_chain_gap_h` หรือไม่

## คำสั่ง build ใหม่

จากรากโปรเจกต์:

```bat
python Oatside\build_oatside_reports.py
```

จากนั้น deploy GitHub Pages ตาม workflow เดิมถ้าต้องการอัปเว็บ
