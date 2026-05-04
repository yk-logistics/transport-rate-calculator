# IMPORT MAPPING SPEC

ที่มาของข้อมูล: `ProjectYK_System/Daily.xlsx` (ตัวอย่างจริงจากทีม) พร้อมไฟล์เต็มใน `Salary/AYU|BigC|LCB/`

เป้าหมาย: กำหนด mapping ระหว่างคอลัมน์ Excel ของแต่ละไซต์ → ฟิลด์กลาง `DailyJob` ในฐานข้อมูล

ตัวย่อ: `R2 = header แถวที่ 2 ของ sheet`

---

## AYU (28 คอลัมน์ ใช้จริง ~18)

| ฟิลด์กลาง (canonical) | R2 header | col# | ประเภท | หมายเหตุ |
|---|---|---|---|---|
| `work_date` | วันที่ | 0 | date | |
| `customer_name` | ลูกค้า | 1 | str | เช่น DHL, Big-C |
| `origin` | ขึ้นสินค้า | 2 | str | ต้นทาง |
| `destination` | ส่งสินค้า | 3 | str | ปลายทาง |
| `plate_no` | ทะเบียนรถ | 4 | str | เช่น 71-0556 |
| `truck_type` | ประเภทรถ | 5 | enum | 6W / 10W / 10WL |
| `driver_raw_name` | ชื่อ-พขร. | 6 | str | ยังไม่ normalize |
| `doc_no` | เลขที่ | 8 | str | เลขเอกสาร/จ็อบ |
| `revenue_customer` | ค่าขนส่ง | 9 | money | รายได้ต่อเที่ยว |
| `fuel_liter` | ลิตร | 12 | number | |
| `fuel_amount` | บาท | 13 | money | ค่าน้ำมัน |
| `mile_snapshot` | ไมล์รถ | 14 | number | เลขไมล์ตอนนั้น |
| `trip_fee_driver` | ค่าเที่ยว พขร. | 16 | money | จ่ายคนขับ |
| `remark` | หมายเหตุ | 17 | str | เช่น "PTT" |

**ลักษณะพิเศษ AYU:**
- ไม่มีคอลัมน์ Status — สถานะงานดูจากค่าในเซลล์เอง
- รถเข้ามาในรายงานเรียงตามทะเบียน (รถจอด/รถว่างก็อยู่ด้วย)
- ประเภทรถมีหลายแบบ: 6W, 10W, 10WL

---

## BIGC (19 คอลัมน์) — รถหัวลาก + หาง

| ฟิลด์กลาง | R2 header | col# | ประเภท | หมายเหตุ |
|---|---|---|---|---|
| `work_date` | วันที่ | 0 | date | (รับงาน) |
| `head_plate` | ทะเบียน (รถหัวลาก) | 1 | str | |
| `tail_plate` | ทะเบียน (หาง) | 2 | str | `-` ถ้าไม่มี |
| `driver_raw_name` | ชื่อ-นามสกุล | 3 | str | |
| `pickup_location` | รับตู้ / สถานที่ | 4 | str | หรือ "รับรถ", "2BH" |
| `store_code` | รหัส / สาขา | 5 | str | |
| `destination` | ที่ส่งสินค้า | 6 | str | |
| `doc_no` | เลขที่เอกสาร | 7 | str | |
| `revenue_customer` | ค่าขนส่ง (โดยประมาณ) | 8 | money | |
| `trip_fee_driver` | ค่าเที่ยว พขร. (จุดพ่วง/BH) | 9 | money | |
| `monthly_salary` | เงินเดือน | 10 | money | **ต้องถามว่าทำไมใส่ต่อแถว** |
| `fuel_station` | น้ำมันที่ (กำหนด) | 11 | str | |
| `mile_snapshot` | เลขไมล์ตอนเติม | 12 | number | |
| `fuel_liter` | จำนวนน้ำมันลิตร | 13 | number | |
| `fuel_price` | ราคาน้ำมัน ฿/L | 14 | money | |
| `fuel_amount` | จำนวน (เงินบาท) | 15 | money | |
| `fuel_rate_target` | เรท (น้ำมัน) | 16 | number | |
| `fuel_amount_budget` | จำนวน (น้ำมันทำได้) | 17 | money | |
| `remark` | หมายเหตุ | 18 | str | |

**ลักษณะพิเศษ BIGC:**
- มี `รับรถ`, `2BH` เป็น placeholder (ไม่ใช่งานจริง)
- มีเงินเดือนผสมในแถวรายวัน (ต้องชัดเจนว่า allocate หรือ lookup)
- มีระบบ "น้ำมันทำได้" (budget vs actual)

---

## LCB (40 คอลัมน์ ใช้จริง ~38) — ตู้ Container Export/Import

| ฟิลด์กลาง | R2 header | col# | ประเภท | หมายเหตุ |
|---|---|---|---|---|
| `work_date` | วันที่ | 0 | date | |
| `job_status` | Status | 1 | enum | MOL/KLND/DHL/KAO/KAO/รถจอด/ลา... ต้องรวบรวม |
| `plate_no` | ทะเบียนรถ | 2 | str | |
| `truck_type` | ประเภท | 3 | enum | 6W / 10W |
| `driver_raw_name` | พนักงานขับรถ | 5 | str | |
| `driver_phone` | เบอร์โทร | 6 | str | |
| `trip_type` | Type | 7 | enum | Export / Import / Domestic |
| `starting_point` | STARTDING (รับตู้เปล่า/ตู้หนัก) | 8 | str | |
| `loading_point` | Loading (บรรจุ/เปิด) | 9 | str | |
| `destination` | Destination (คืนตู้/ลงท่า) | 10 | str | |
| `job_ref` | Job. | 11 | str | เลขงาน |
| `container_no` | เบอร์ตู้ | 12 | str | |
| `container_size` | ขนาด/ตู้กลับAAT | 13 | str | เช่น 40 |
| `lift_fee` | ค่ายกตู้ | 14 | money | |
| `yard_fee` | ค่าผ่านลาน | 15 | money | |
| `clean_fee` | ค่าคลีน | 16 | money | |
| `shore_fee` | ค่าชอร์ | 17 | money | |
| `port_entry_fee` | เข้าท่า | 18 | money | |
| `weighing_fee` | ค่าชั่งน้ำหนัก | 19 | money | |
| `revenue_customer` | ค่าขนส่ง | 20 | money | |
| `revenue_total` | รวมเก็บค่าขนส่ง | 21 | money | รวมทุกค่าที่เก็บลูกค้า |
| `invoice_no` | ออกอินวอย | 22 | str | |
| `invoice_date` | ลงวันที่ | 23 | date | |
| `wht_53` | ยอดหัก ภงด.53 | 24 | money | |
| `mile_snapshot` | ไมล์ | 25 | number | |
| `fuel_liter` | น้ำมัน(ลิตร) | 26 | number | |
| `fuel_amount` | น้ำมัน(บาท) | 27 | money | |
| `fuel_rate_km_per_l` | เรท กม/ล | 28 | number | |
| `trip_fee_driver` | ค่าเที่ยว พขร. | 29 | money | |
| `extra_pickup_return` | รับตู้/คืนตู้แทน | 30 | money | |
| `extra_special` | พิเศษ | 31 | money | |
| `extra_ot` | OT | 32 | money | |
| `shared_vehicle` | ใช้รถร่วม | 33 | str | |
| `receive_inv_no` | Receive/Inv.No. | 34 | str | |
| `remark` | หมายเหตุ | 35 | str | |
| `mflow` | M-Flow | 36 | money | ค่าทางด่วน |
| `vehicle_check` | เช็ครถ | 37 | str/flag | |

**ลักษณะพิเศษ LCB:**
- ใช้ Status column เป็นตัวจำแนกลูกค้า/ประเภทงาน (ต้องทำ enum)
- มีค่าต่าง ๆ แยกย่อยมากกว่า (lift/yard/clean/shore/port/weighing)
- มี extra payments หลายแบบ (รับตู้แทน, พิเศษ, OT)

---

## ฟิลด์ที่ยัง **ไม่อยู่** ในโมเดล `DailyJob` ปัจจุบัน

จะต้องเพิ่มในเฟสถัด ๆ ไป:

- ต่อเติม `DailyJob`: `doc_no`, `fuel_liter`, `fuel_amount`, `mile_snapshot`, `container_no`, `trip_type`, `invoice_no`, `invoice_date`, `wht_53`, `shared_vehicle`, `mflow`, `vehicle_check`
- แยกตาราง: `daily_job_fees` (lift/yard/clean/shore/port/weighing/special/ot/pickup_return) — แทนที่จะเพิ่มคอลัมน์เยอะ
- แยกตาราง: `trucks` (head/tail, type) และ `trailers`
- แยกตาราง: `fuel_txns` (linked to daily_job_id)

---

## Status ที่ต้องยืนยันกับทีม (คำถามเปิด)

1. LCB `Status`: ค่าที่เป็นไปได้ทั้งหมด? (เห็นเบื้องต้น MOL/KLND/DHL/KAO/รถจอด/ลา-ไม่พร้อม — คาดว่าเป็น "ลูกค้า/ประเภทงาน" + "สถานะรถ")
2. BIGC `รับตู้` col 4: ค่าที่ใช้จริง? (เห็น "รับรถ", "2BH", "สถานที่จริง" — เป็นตัวเดียวกันหรือแยก?)
3. BIGC `เงินเดือน` col 10: ใส่ต่อแถวหมายถึงอะไร? allocate เงินเดือนต่อเที่ยว หรือแค่ lookup?
4. AYU ไม่มี `ประเภทรถ 10WL` ใน BIGC/LCB — มีอีกไหม?
5. ทีมคีย์ "ทุกงาน 1 แถว" หรือ "ทุกแถวต่อรถต่อวัน" (เพราะ AYU มี placeholder ว่างอยู่ด้วย)?
6. ใครคีย์แต่ละไซต์? ทีม OP 3 คนแบ่งไซต์หรือช่วยกันทุกไซต์?
7. คีย์ตอนไหน: realtime ตอนเสร็จงาน, ตอนสิ้นวัน, หรือวันรุ่งขึ้น?
