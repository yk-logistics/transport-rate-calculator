---
name: project-preecha-petty
description: "ปรีชา (คนใหม่ AYU 165) สดย่อย 4,095 ไม่ได้หัก — insert 5 รายจากไฟล์ + recompute — DONE+deployed"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5958b1e8-62e6-4533-af2d-1c3e111a9801
---

DONE+deployed 30มิ.ย. (DB-only): ปรีชา165 (คนใหม่ ayu_trip [[project-ayu-jun-new-drivers]]) สดย่อยไม่หัก — ตอน onboard petty ยังไม่อยู่ใน DB. ดึงจากไฟล์ `สดย่อยวังน้อย หมิว.xlsx` ชีท JUN26 (ผู้เบิก="ปรีชา" col O): 5 ราย = **4,095** (20/6 500, 22/6 1000, 23/6 95 ทางด่วน, 25/6 500, 29/6 2000).

insert PettyCashTxn 5 ราย (driver_id=165, site=AYU, cyc=2026-06, deduct_from_driver=1, deduction_status=pending, source=ayu_petty_itemized) → recompute ปรีชา in-place: net 4,569→**474** (petty 4,095). run18 241,988→**237,893**; net_guard รอบอื่นนิ่ง; live public 200, 5 petty rows.

**สุธรรม168 (ออกแล้ว) ด้วย:** สดย่อย col O = **2,550** (3 ราย: 9/6 เสื้อสะท้อนแสง 150, 17/6 ค่าเติมเน็ต 400, 17/6 อุบัติเหตุ 2,000; ราย O=0 ค่าข้าว/พ่วงแบต ไม่หัก). insert+recompute → net 1,717→**−833** (ทำ 2 วัน=1,800 แต่สดย่อย 2,550 → **ติดลบ=เป็นหนี้บริษัท 833** เพราะออกแล้ว). run18 →**235,343.34**.

**บทเรียน:** คนใหม่ที่ onboard ก่อน petty import → ต้องตามลงสดย่อยทีหลัง (ปรีชา 4,095 + สุธรรม 2,550; ธนา O=0 ไม่มีหัก). related: [[project-ayu-jun-new-drivers]], [[project-payroll-slip-petty-itemize]], [[project-ayu-office-reconcile-rup]]
