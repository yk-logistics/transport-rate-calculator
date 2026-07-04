---
name: project-deposits-overview-page
description: หน้าเงินประกันตนรวม /deposits — ดูยอดทุกคน + แก้ inline + ประวัติรายคน; DONE+deployed 2026-06-28
metadata: 
  node_type: memory
  type: project
  originSessionId: 63c19335-493e-4f48-b57d-49d841584be5
---

DONE + deployed live 2026-06-28: หน้า `/deposits` (เมนู เงิน → 🔒 เงินประกันตน) ให้ โอ ตรวจเงินประกันตน (driver security deposit / เงินค้ำ) ของทุกคนในที่เดียว.

**UPDATE 2026-06-28 (filter คนออกแล้ว):** เพิ่มกรองสถานะ — default แสดงเฉพาะ `status='active'` (18 คน), ปุ่มสลับ "รวมคนออกแล้ว (84)" → `?show=all` แสดง inactive ด้วย (102 รวม). summary นับเฉพาะคนที่แสดง. route param `show` (default "active"), `resigned_count` เคารพกรองไซต์. deployed live (filter present + 18/84/102 ยืนยันบน server). status สะอาด: active/inactive ชัด ไม่มีเคสกำกวม (active+end_date=0).

**บทเรียน cross-session contamination:** ระหว่างทำ filter มี Claude อีก session แก้ payroll/tax (YTD ภาษี) ใน working tree เดียวกันพร้อมกัน. commit แรกของ filter (5d4f9f3) `git add main.py` เลย**ดูดโค้ด payroll ของ session อื่นที่ยังไม่ commit ติดไปด้วย** → 3 payroll tests fail ในชุดรวม (รันแยกผ่าน). branch label ถูกสลับใต้มือ (ดู [[reference-branch-switch-during-session]]). วิธีกู้: ทิ้ง commit ปน, สร้าง branch ใหม่จาก main สะอาด, re-apply เฉพาะ hunk ของ deposits (diff main.py 19 บรรทัด ไม่ใช่ 39), verify `grep ytd_by_emp=0` ก่อน merge. **กฎ: ถ้ามี session อื่นทำ repo เดียวกัน อย่า `git add <file>` ที่ session อื่นอาจแก้ — ใช้ `git add -p` หรือ stage เฉพาะ hunk; verify diff ไม่มี symbol ของงานอื่นก่อน commit.**

**สิ่งที่ทำ:**
- ตารางรวม: คนที่ `deposit_target>0` (102 คน LCB ตอน deploy, สะสมรวม 290,000), summary บน + progress bar + กรองไซต์
- แก้ยอด inline (สะสม/เพดาน) + audit ทุกครั้ง → model ใหม่ `DepositAudit` (schema v27→**28**); ค่าไม่เปลี่ยน=ไม่ log, ติดลบ=reject 400
- ประวัติการหักรายคน จาก `payrunitem.deposit_install` + เตือน "ยอดยกมา/ตั้งค่า (ไม่ได้หักผ่านระบบ)" = balance − Σประวัติ
- 8 tests (`app/tests/test_deposits.py`); **ไม่แตะ payroll engine** (server net 3,985,960 เท่าเดิมก่อน/หลัง)

**ข้อมูลจริงที่เจอ:** เงินประกันตน = 2 field static บน Employee (`deposit_balance`/`deposit_target`); การหักรอบละ 1,000 ใน `payroll.py:1159`. ตาราง `DriverDeposit` (models.py) มีนิยามแต่**ไม่เคยใช้** (ไม่ activate). ประวัติหักผ่านระบบมีจริงแค่ LCB พ.ค./มิ.ย. (12 คน) เพราะไซต์อื่นลอกยอด net มา → หน้าเลยโชว์ส่วนต่าง "ยอดยกมา".

**Deploy gotcha เกิดซ้ำ** (ดู [[reference-mvp-deploy-restart-gotcha]]): deploy_mvp_to_server.sh kill-filter `CommandLine -match 'YK_MVP'` **พลาด** process จริงที่ฟัง 8010 เพราะมันรันใต้ **global python** (`AppData\Local\Python\pythoncore-3.12-64\python.exe main.py`) — cwd=YK_MVP แต่ CommandLine ไม่มีคำว่า YK_MVP. หลัง deploy schema ยังค้าง 27. **Fix ที่ใช้ได้:** kill ทุก python ที่ match `main\.py` และ `-notmatch YK_LINE_ARCHIVER` (ไม่ใช่ match YK_MVP) → Stop-ScheduledTask ก่อน kill → Start → verify schema=28 ผ่าน public /health. SSH→PowerShell quote ซ้อนพัง ต้อง scp .ps1 ไปรัน -File.

spec: `docs/superpowers/specs/2026-06-28-deposits-overview-page-design.md` · plan: `docs/superpowers/plans/2026-06-28-deposits-overview-page.md`

**Pre-existing test failure (ไม่ใช่จากงานนี้):** `tests/test_check_link_menu.py::test_admin_sees_check_links_menu` fail บน main อยู่แล้ว — เทสต์หา text "ลิงก์ตรวจยาง" + gate `/admin/check-links` แต่ base.html:133 ใช้ "🔗 ลิงก์ตรวจสภาพรถ" + gate `/admin/users`. ยังไม่แก้ (นอก scope) — โอ ตัดสินใจ.
