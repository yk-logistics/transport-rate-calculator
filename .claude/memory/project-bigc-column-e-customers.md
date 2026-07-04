---
name: project-bigc-column-e-customers
description: BigC daily column E (สถานะงาน) → customer map; key for costing(I) + CFO customer breakdown
metadata: 
  node_type: memory
  type: project
  originSessionId: 09916d86-fbc0-4c5a-bfc8-46e13949f62c
---

BigC เดลี่ ชีท `เดือนNN.NN` **คอลัมน์ E = สถานะงาน/ประเภทงาน** (ไม่ใช่ origin/รับตู้ ตามที่ import แรก map ผิด). โอยืนยัน 29มิ.ย. ว่า E map เป็นลูกค้าได้:

| E (ขึ้นต้น/รหัส) | ลูกค้า | งาน |
|---|---|---|
| 1BH, 2BH, 1BigC, 2BigC, 2DV, 2++, 1++ (ทุกอย่างขึ้นต้น 1/2 + BH/BigC/DV/++) | **BigC** | บิ๊กซี — 1=สาขา กทม., 2=สาขา ตจว., ++/พ่วง=หลายสาขา (คิดค่าขนส่ง=สาขาไกลสุด+ค่าพ่วงตามจำนวนพ่วง), BH=backhaul, DV=(ประเภทบิ๊กซี) |
| **ABF** | DHL | งาน AB Food |
| **Homepro** | Homepro | Homepro |
| **Oatside** | DHL | Overflow (Oatside) — งานเดียวกับ DHL Overflow ของแหลม [[project-dhl-overflow-rate]] |

นับจริงเดือน พ.ค.2026: Oatside 141, 2BigC 78, 2++ 33, 2BH 29, ABF 18, รับรถ 11, Homepro 2, 1BH 1, 2DV 1.

**ใช้ทำอะไร:** (1) คิดค่าขนส่ง(ช่อง I) จากสถานะงาน [[project-bigc-may-payroll]] — ยังรอเรทต่อสาขา+ค่าพ่วง; (2) CFO โชว์ว่าเที่ยวไหนลูกค้าอะไร [[project-cfo-revenue-drilldown]]. โอตอบ session อื่นไว้ด้วยเรื่องรหัสประเภทงานนี้ (สำหรับ CFO).

**ติด:** import แรก (import_bigc_daily.py) ยังไม่เก็บ E เป็น field แยก (map ไป origin). ต้องเพิ่ม field สถานะงาน/ลูกค้า ก่อนทำ costing+CFO. (related [[project-bigc-daily-import]])
