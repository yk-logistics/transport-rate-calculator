---
name: project-transfer-total-positive-only
description: "หน้าโอนเงิน: ยอดรวม=เฉพาะ net>0 (ไม่หักยอดติดลบ) + ตัวอักษรพิมพ์ใหญ่ขึ้น — DONE+deployed"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5958b1e8-62e6-4533-af2d-1c3e111a9801
---

DONE+deployed 30มิ.ย. (main 7149169, code-only): โอ — หน้าโอนเงิน ยอดรวม**ห้ามเอายอดติดลบไปหัก** เพราะยอดรวม=เงินที่ต้องเตรียมโอนให้คนที่ได้จริง; คนติดลบ (ธัชชนพล −35,950, สุธรรม −833 = เป็นหนี้บริษัท) ถ้าเอามาหัก → เตรียมเงินไม่พอ.

**fix:** `payroll_print_all` route เพิ่ม `totals["transfer"] = Σ net เฉพาะ net>0` + `transfer_count`. หน้าโอนเงิน (template payroll_print_all.html block 2) ใช้ `totals.transfer/transfer_count` แทน `totals.net` (header "ยอดเตรียมเงินโอนรวม" + tfoot "ไม่รวมยอดติดลบ"). **หน้าสรุป (block 1) ยังใช้ totals.net เดิม** (เป็นสรุป ไม่ใช่ยอดโอน). run18: net รวม 246,193.34 → ยอดเตรียมโอน **282,976.28** (29/31 คน, ต่าง 36,782.94=ยอดติดลบ 2 คน).

**+ตัวอักษรพิมพ์ใหญ่ขึ้น + เต็ม 2 หน้า (main 98263c2):** print CSS `table.run:not(.boss)` font→**18px**, num 19px, totband 26/32px, page-break-inside:avoid ต่อแถว. **JS `_fitEl` เพิ่ม widthOnly param** สำหรับ `.block` → ย่อเฉพาะกว้างเกิน (boss table) **ไม่ย่อตามความสูง** → หน้าโอนเงินหลายคนไหลข้ามหน้าเอง ตัวไม่หด (เดิม shrink-to-1-page ทำตัวเล็ก). 31 คน เต็ม 2 หน้า. **ยกเว้น boss** (คอลัมน์เยอะ คงเล็ก/ย่อกว้าง). 17 tests pass. related: [[project-payroll-bank-print.md]], [[project-ayu-office-reconcile-rup]]
