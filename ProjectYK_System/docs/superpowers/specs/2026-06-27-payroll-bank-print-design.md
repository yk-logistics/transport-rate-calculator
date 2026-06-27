# หน้าบัญชีคนขับ + ปุ่มพิมพ์เงินเดือนรวม

วันที่: 2026-06-27
สถานะ: design approved (โอ 2026-06-27)
Branch: `feat/payroll-bank-print`

## ปัญหา / เป้าหมาย

โอต้องการปุ่มเดียวที่พิมพ์เงินเดือนทั้งรอบผ่านเบราว์เซอร์ (Ctrl+P) ได้ครบ 3 ส่วน:
หน้าสรุปทุกคน, หน้าโอนเงิน (ชื่อ+บัญชี+จำนวนโอน+หมายเหตุ), สลิปรายคน.
ปัจจุบันมีปุ่ม export PDF เป็นไฟล์อยู่แล้ว (`payroll_export_pdf.py`) แต่เลขบัญชีอยู่ใน
JSON และไม่มีหน้าพิมพ์สดในเบราว์เซอร์. โอเลือก: เก็บปุ่ม export ไฟล์เดิม + เพิ่มปุ่มพิมพ์สด,
ย้ายเลขบัญชีเข้า DB (แยก bank_name + account_no).

อ้างอิงไฟล์จริง: Excel sheet "BANK" (โอส่ง 2026-06-27) — 21 คน, คอลัมน์ G สีแดง = เลขบัญชีล่าสุด
(ไทยพาณิชย์/กรุงศรี/กรุงไทย/กสิกร), หมายเหตุเห็น: ออก / เหมาน้ำมัน / ออกไปBigC / คืนประกันตน,
ยอดติดลบแสดงได้ (วิชาญ −300, สุภาพ −4,467).

## Scope

1. Schema: Employee.bank_name + account_no; PayRunItem.transfer_note
2. Backfill เลขบัญชีจาก Excel BANK (script ครั้งเดียว, map by ชื่อ)
3. UI กรอกบัญชีในหน้าแก้ไขพนักงาน
4. หน้าพิมพ์สด `/payroll/{run}/print` (สรุป → โอนเงิน → สลิปรายคน)
5. ปุ่ม "พิมพ์ทั้งหมด" ในหน้า payroll detail
6. หมายเหตุโอนเงิน: auto + แก้มือ (POST บันทึก transfer_note)

นอก scope: ไม่แตะ engine คำนวณเงิน (net ไม่เปลี่ยน); ไม่ลบ export PDF เดิม; ไม่ลบ bank JSON.

## ส่วนที่ 1 — Schema (v27)

Employee เพิ่ม:
```
bank_name: str = Field(default="")      # "ไทยพาณิชย์" / "กสิกร" / ...
account_no: str = Field(default="")     # "688-444-0533"
```
PayRunItem เพิ่ม:
```
transfer_note: str = Field(default="")  # หมายเหตุหน้าโอนเงิน (แก้มือ override auto)
```
Migration: bump SCHEMA_VERSION 26→27, `_ensure_column` 3 บรรทัด (ทุกตัว default "" — regression-safe).

## ส่วนที่ 2 — Backfill เลขบัญชี (script ครั้งเดียว)

`tools/backfill_bank_accounts.py` (ad-hoc): อ่าน mapping ชื่อ→(ธนาคาร,เลข) จาก Excel BANK
(หรือ hard-code dict 21 คนที่อ่านจากภาพ — โอจะส่งไฟล์/ยืนยันเลข). Match Employee by
first-name (เหมือน [[project-lcb-jun-xlsx-reimport]] first-name→id map). อัปเดต by id.
รายงานคนที่ match ไม่ได้ให้กรอกมือ. ไม่ทับเลขที่มีอยู่ (ถ้ามี).

## ส่วนที่ 3 — UI กรอกบัญชี (หน้าแก้ไขพนักงาน)

หน้าแก้ไข Employee เพิ่ม 2 ช่อง: ธนาคาร (text/select), เลขบัญชี (text). POST เดิมของหน้า
employee edit รับ field เพิ่ม. ตามรูปแบบฟอร์มที่มีอยู่.

## ส่วนที่ 4 — หน้าพิมพ์สด `/payroll/{run}/print`

Route ใหม่ GET `/payroll/{run_id}/print` → template `payroll_print_all.html`.
โหลด PayRun + PayRunItem ทั้งหมด (เรียงเหมือนหน้า detail) + Employee (bank).
3 บล็อก, แต่ละบล็อก `page-break-before: always`:

1. **สรุปทุกคน**: ตารางเหมือน payroll_detail (รายได้ − น้ำมัน = รายได้หลังหักน้ำมัน − หัก = สุทธิ).
2. **โอนเงิน**: ตาราง ลำดับ | ชื่อ-สกุล | ธนาคาร เลขบัญชี | จำนวนโอน (=net_pay, ติดลบได้) | หมายเหตุ.
   - หมายเหตุ = transfer_note ถ้ามี, ไม่งั้น auto: `_auto_transfer_note(emp,item)`:
     status≈ลาออก/end_date≤period → "ออก"; deposit คืน (deposit refund ในรอบ) → "คืนประกันตน";
     pay_mode mao/mixed → "เหมาน้ำมัน". (auto เป็น hint; โอแก้ทับได้)
   - แถวหมายเหตุแก้มือ: form inline POST `/payroll/{run}/employee/{emp}/transfer-note` (no-print).
3. **สลิปรายคน**: loop employees, include `payroll_slip.html` แบบ per-employee (มีรายได้หลังหักน้ำมันแล้ว),
   page-break ต่อคน. ถ้า include ซับซ้อน (slip ต้อง context เฉพาะคน) → render slip block inline
   ด้วยข้อมูล item เดียวกัน (subset ของ payroll_slip ที่ไม่พึ่ง route-level ctx).

ปุ่มในหน้า print: "พิมพ์ (Ctrl+P)" `window.print()`; `@media print` ซ่อนปุ่ม/ฟอร์มแก้หมายเหตุ.

## ส่วนที่ 5 — ปุ่มในหน้า detail

เพิ่มปุ่ม **"🖨 พิมพ์ทั้งหมด"** (link เปิด `/payroll/{run}/print` แท็บใหม่) ข้างปุ่ม "ส่งออก PDF" เดิม
(ปุ่ม export ไฟล์ยังอยู่).

## ส่วนที่ 6 — แก้หมายเหตุโอนเงิน

POST `/payroll/{run_id}/employee/{emp_id}/transfer-note` (Form: note) → set
PayRunItem.transfer_note → redirect กลับหน้า print. ไม่ recompute (ไม่กระทบเงิน).
Locked เมื่อ run finalized.

## เทสต์

- migration: 3 field ใหม่ default "" → เหมา/ทุกคน net เท่าเดิม (regression)
- `/payroll/{run}/print` render 200, มี 3 บล็อก (สรุป/โอนเงิน/สลิป), จำนวนแถวโอนเงิน = จำนวนคน
- net แต่ละคนในหน้าโอนเงิน = net_pay จริง (รวมติดลบ)
- transfer_note: POST แล้วแสดงทับ auto
- _auto_transfer_note: ลาออก→"ออก", เหมา→"เหมาน้ำมัน"

## Deploy

- branch → merge main → deploy: code (templates+main+models) scp + **app.db full-file overwrite**
  (เพราะ backfill bank + transfer_note อยู่ใน DB) — backup server ก่อน, restart by port-owner
  ([[reference-mvp-deploy-restart-gotcha]], SSH ใช้ -EncodedCommand).
- payrun#2 ยัง draft.

## ความปลอดภัย

- ไม่แตะ engine → net ไม่เปลี่ยน (verify regression ก่อน deploy)
- backfill by id, ไม่ทับเลขที่มี, รายงาน unmatched
- backup app.db ก่อน backfill + ก่อน deploy
