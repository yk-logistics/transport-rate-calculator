---
name: project-samai-petty-split-ayu-bigc
description: "สดย่อยสมัย ปนข้ามไซต์ — แยกสมัย อยุธยา(AYU137) ออกจากสมัย BIG C(BIGC104), ย้าย 8 รายไป BIGC — DONE+deployed"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5958b1e8-62e6-4533-af2d-1c3e111a9801
---

DONE+deployed 30มิ.ย. (DB-only, ไม่แตะโค้ด): มี 2 คนชื่อ "สมัย" คนละไซต์ — **สมัย อยุธยา = AYU emp137 (ayu_trip)** vs **สมัย ราศรี = BIGC emp104 (bigc_monthly)**. petty_itemize ผูกผิด: 8 รายของ "สมัย BIG C" (requester_raw) หลุดไปอยู่ใต้ driver_id=137 (AYU) → หักเงินสมัย AYU เกิน.

**แยกด้วย requester_raw:** "สมัย อยุธยา" 13 ราย=9,925 (ถูก เก็บไว้ที่ 137) / "สมัย BIG C" 8 ราย=9,500 (ผิด ids 257,278,306,326,351,390,412,427). โอสั่ง**ย้ายไปสมัย BIGC(104)**: UPDATE driver_id 137→104, site_code AYU→BIGC, pay_cycle_tag=เดือนปฏิทินของ txn_date (id257 20/5→2026-05, อีก 7 มิ.ย.→2026-06). **ต้องแก้ครบ 3 ฟิลด์** เพราะ `_sum_petty_cash_deduction` filter ทั้ง driver_id + pay_cycle_tag + site_code(หรือ ว่าง/null) — แค่ flip driver_id ทิ้งไว้ site=AYU จะ orphan (ไม่เข้า BIGC).

recompute เฉพาะ สมัย137 in-place (ayu_trip ไม่ใช่ mao → mao-tool ไม่แตะ; เขียน inline calc_one_employee→set 28 fields): petty 19,425→**9,925**, net **−5,975→+3,525** (Δ+9,500, หายติดลบ!). run18 195,067.46→**204,567.46**. net_guard --allow 18 OK; **BIGC run4(2026-05) ไม่ recompute** → id257(พ.ค.)จะเข้า BIGC สมัยเมื่อโอคิด BIGC เอง (ยังไม่มี BIGC payrun 2026-06; 7 รายรอรอบนั้น). live: สมัย137 net 3,525 petty 9,925(13ราย), public 200.

**UPDATE 30มิ.ย.: สมัย อยุธยา137 ไม่มีประกันสังคม** → ตั้ง ss_exempt (เดิม imputed base 9000→SS 450), recompute net 3,525→**3,975** (+450), run18→240,193.34, net_guard นิ่ง, live ok.

**UPDATE 30มิ.ย.(2): สดย่อย คีย์ผิดอีก 1 ราย** — petty id291 (4/6 เงินเบิก 1,000) คีย์เป็น สมัย อยุธยา ผิด → **โยกไป สมัย BIGC104** (driver_id 137→104, site AYU→BIGC, cyc→2026-06, requester→"สมัย"). สมัย อยุธยา petty 9,925→**8,925** net 3,975→**4,975** (+1,000), run18→**241,193.34**; BIGC ไม่ขยับ (ยังไม่มี payrun มิ.ย.). **ไฟล์ต้นทาง สดย่อยวังน้อย หมิว.xlsx โอแก้เอง** (petty ไม่ได้ดึงจาก gsheet).

**บทเรียน: ชื่อซ้ำข้ามไซต์ → เช็ค requester_raw/memo ไม่ใช่แค่ driver_id**; AYU เป็น cycle 26→25, BIGC เป็นเดือนปฏิทิน. related: [[project-payroll-slip-petty-itemize]], [[project-ayu-jun-payroll]], [[project-bigc-may-payroll]]
