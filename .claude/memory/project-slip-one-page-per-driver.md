---
name: project-slip-one-page-per-driver
description: Slip auto-fits to 1 A4 page per driver (zoom) — long daily+petty no longer overflow
metadata: 
  node_type: memory
  type: project
  originSessionId: 09916d86-fbc0-4c5a-bfc8-46e13949f62c
---

DONE+deployed 29มิ.ย.: สลิป **1 คน = 1 หน้า A4** ทุกสลิป (โอ: บางคนตารางเดลี่+รายการหักสดย่อยยาวล้นไปหน้า 2). แก้ทั้ง `payroll_slip.html` (หน้ารายคน) + `payroll_print_all.html` (พิมพ์รวม/ZIP).

**2 ชั้น:**
1. **CSS dense/ultra** (payroll_slip.html): `daily_jobs|length >38` = `.dense`, `>52` = `.ultra` → ย่อ font/padding ตาราง daily + panel + petty lines + net-box.
2. **JS auto-fit (`fitOnePage`)**: ถ้า `.slip` สูงเกิน ~1010px (A4 portrait usable ~1040) → set `slip.style.zoom` (ลด layout height **จริง** ลดจำนวนหน้า — **ต่างจาก `transform:scale` ที่ visual-only ไม่ลดหน้า!**). วน 5 รอบปรับ zoom ให้ลู่เข้า (อิง `getBoundingClientRect().height`), floor 0.42. fire on load + beforeprint + `document.fonts.ready` + setTimeout(400) เผื่อ webfont ช้า.

print-all: zoom ต่อ `.slip` block ทุกอัน + เรียก `fitSlipsOnePage()` ก่อน ZIP html2pdf (PDF ต่อคน 1 หน้า).

**verified headless Chrome (จำนวนหน้า PDF จริง):** เรวัตร(58 เดลี่+41 petty)→1หน้า zoom 0.62, มานพ(55)→1, สุรเดช(38 mixed-mode)→1; AYU print-all 24 คน = 26 หน้า (24 สลิป + 2 สรุป/โอนเงิน). ย่อแล้วยังอ่านออก.

**fit เช็คทั้งสูง+กว้าง (สำคัญ):** หน้า **boss/ผู้บริหาร** (`?for=boss`) มีคอลัมน์เพิ่ม (ค่าขนส่งจริง+ราคากลาง+KB) → ตารางกว้าง ~1068px > A4 usable กว้าง ~720px. fit รุ่นแรกเช็คแค่ "สูง" → boss ยังเกิน 1 หน้า (โอเจอ). แก้: `zoom = 1/max(overH, overW)` โดย `PAGE_H=1010, PAGE_W=720`. print-all fit `.block` (สรุป/โอนเงิน boss กว้างเกินด้วย). verified BOSS LCB print-all 26→20 หน้า.

**GOTCHA (native print):** `transform:scale` ไม่ลดจำนวนหน้าพิมพ์ (visual เฉยๆ) — `window.print()` ต้องใช้ `zoom`. puppeteer `p.pdf()` ไม่ fire `beforeprint` → ต้อง fit ตอน load. mixed-mode slip (lcb_mixed) ใช้ table branch คนละอันแต่ zoom ครอบ `.slip` ทั้งก้อนเลยครอบคลุมหมด. หน้า boss อยู่เฉพาะ print-all (`?for=boss`); single-slip page เป็น driver view เสมอ.

**GOTCHA (ZIP แยกไฟล์ต่อคน — กลับด้านกับ native print!) — fixed 29มิ.ย.:** ปุ่ม "แยกไฟล์ต่อคน (ZIP)" ใช้ **html2pdf 0.10.1 → html2canvas 1.4.1** ซึ่ง **"ไม่รู้จัก CSS `zoom`" เลย (รู้จักแต่ `transform`)** — ตรงข้ามกับ native print. ถ้าย่อสลิปด้วย `zoom` แล้วให้ html2canvas จับ → มันจับจาก layout เต็มขนาดเดิม ตัวอักษรซ้อนกัน (โอเจอที่หัวสลิป: ช่วงงวด/รอบ/ชื่อ ทับกัน). **แก้:** ตอนทำ ZIP เคลียร์ zoom → วัด scale (`_measureScale`) → ย่อ **clone** ด้วย `transform:scale` ใน box ขนาดหลังย่อ (overflow:hidden) นอกจอ → จับ box นั้น → ภาพถูก + ยังพอ 1 หน้า/คน (html2pdf จับ element เป็น 1 canvas image → page-count คุมด้วยขนาด canvas ไม่ใช่ CSS page-break ฉะนั้น transform ใช้ได้). **กฎจำ:** native print = `zoom`; html2canvas/html2pdf = `transform`. verified headless Chrome: zoom→ตัวอักษรซ้อน, transform→หัวสลิปอ่านออกครบ, PDF 1 หน้าทั้งคู่.

deploy code-only (2 templates) + verify ไฟล์ server (FIT_OK).

**UPDATE 29มิ.ย. — รวมดีไซน์ (โอชอบหน้ารายคน ปุ่มพิมพ์ไม่สวย):** เดิมมี **2 ดีไซน์สลิป** — หน้ารายคน `/employee/{id}/slip` (`payroll_slip.html`, สวย: header-line/driver-line/row-grid/panel/net-box) vs ปุ่มพิมพ์ `/print` (`payroll_print_all.html`, แน่นเก่า grid2/line). โอชอบอันสวย → **รวมเป็น partial `templates/_slip_body.html`** (body สลิปสวยทั้งก้อน). `payroll_slip.html` include 1 ครั้ง (เก็บ JS petty-filter interactive ที่ใช้ id เดียว). `payroll_print_all.html` วน `{% with daily_jobs=r.ctx.daily_jobs, item=r.ctx.item, ... %}{% include "_slip_body.html" %}` ต่อคน + ยก pretty CSS มาด้วย; print route (`/payroll/{id}/print`) เก็บ `r.ctx`=full `build_payroll_slip_context` ต่อคน. petty-filter controls เป็น `no-print` → print-all ไม่ต้องรัน JS (โชว์ static ครบ). **GOTCHA: main.py แก้ route → ต้อง restart** (template เปลี่ยน reload เองแต่ route logic ไม่). verified: print-all คนขับ+boss 20 หน้า (18 คน 1-หน้า + 2 สรุป), ZIP 18 PDF สวย, หน้ารายคนไม่ regression.

related: [[project-payroll-slip-zip-per-driver]], [[project-payroll-slip-petty-itemize]], [[project-slip-fuel-deduct-clarity]], [[project-slip-route-display]]