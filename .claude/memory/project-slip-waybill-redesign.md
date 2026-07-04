---
name: project-slip-waybill-redesign
description: "Slip redesigned \"Waybill\" style (navy/brass/paper) on screen, white bg on print to save ink"
metadata: 
  node_type: memory
  type: project
  originSessionId: 09916d86-fbc0-4c5a-bfc8-46e13949f62c
---

DONE+deployed 29มิ.ย. (Effort Max): ออกแบบสลิปใหม่ ทิศทาง **"Waybill / เอกสารเดินรถ"** ตามที่โอขอ (สวยมีระดับ + minimal สะอาด, ตารางเดลี่=สรุปเงินน้ำหนักเท่ากัน).

**design tokens:** ink navy `#15233f` + brass `#b07d2b` + paper `#fbfaf6` + pos/neg เขียว/แดง. fonts **IBM Plex Sans Thai + IBM Plex Mono** (CDN Google Fonts; ตัวเลขเงิน tabular). eyebrow headers (ตัวพิมพ์ใหญ่ letter-spaced).
**signature = money ribbon** บนสุด: รวมรายได้ → −ค่าน้ำมัน → −เงินหัก → **ยอดสุทธิ** ไหลเป็นเส้นทาง (seg มี ::before รูปลูกศร).
layout: masthead → who-strip (4 ช่อง) → ribbon → 2-col body (ซ้าย=ตารางเดลี่, ขวา=สรุปเงิน+เงินหัก+gauge). หน้าสรุป/โอนเงินเข้าชุด (doc-kind badge + totband + table.run).

**ปริ้นพื้นขาวประหยัดหมึก (โอเน้น):** บนจอสีเต็ม แต่ `@media print` พื้นทึบทุกที่ (ribbon/totband/who/mast/badge/tags) → **ขาวสนิท `!important` + เส้นกรอบ + ตัวอักษรดำ**; ribbon.net/totband ใช้ `border-left:3px double #000` แทนพื้นทอง; eyebrow brass→ดำ. โอบอกชัด: "พื้นไม่ต้องเป็นสีตอนปริ้น ไม่งั้นต้องใช้สีทั้งหน้า".

**โครงสร้างไฟล์:** CSS (`.wb-*` + `.block/.run/.totband` + density + print) อยู่ใน `<style>` ของ payroll_slip.html **และ** payroll_print_all.html (เหมือนกัน, ใส่ผ่าน scratchpad/apply_css.py). markup สลิป = partial `_slip_body.html` (เขียนใหม่เป็น Waybill, **คง Jinja logic ทุก pay_mode เดิม**: mixed/normal table, รายได้/เงินหักแยกตาม mode, petty filter interactive[no-print], fuel หักจริง/ไม่หัก/วัดถัง). หน้าสรุป/โอนเงิน = block ใน payroll_print_all.html.

**คง:** 1คน1หน้า (density dense/ultra + zoom-fit สูง+กว้าง [[project-slip-one-page-per-driver]]), boss mode, ZIP per-driver, petty itemize, fuel clarity. verified PDF 20 หน้า (18 คน + 2 สรุป), ปริ้น grayscale พื้นขาว, petty filter+boss ทำงาน.

related: [[project-slip-one-page-per-driver]], [[project-payroll-slip-zip-per-driver]], [[project-slip-fuel-deduct-clarity]], [[project-payroll-slip-petty-itemize]]