---
name: project-transfer-bank-fix-paikai-ruangrit
description: "30มิ.ย. หน้าโอนเงิน: แก้เลขบัญชีสลับแถว+ใส่นามสกุล, เพิ่มป้าไก่แม่บ้าน, คืนประกันเรืองฤทธิ์, รุ่งเรืองบัญชีซ้ำ — DONE+deployed live"
metadata: 
  node_type: memory
  type: project
  originSessionId: beb23090-b706-49e1-a868-7473f9f23c81
---

โอ 30มิ.ย.: หน้าโอนเงิน MVP มีเลขบัญชีผิด + อยากให้โชว์ชื่อ-นามสกุลเต็ม. ทำบน app.db local, AYU run#18 (draft, cycle 2026-06). **ยังไม่ deploy DB ขึ้น server** (รอโอ go + probe ก่อนกัน clobber งาน session อื่น).

**สาเหตุเลขบัญชีผิด = สลับเลื่อน 1 แถว** (off-by-one เวลาคีย์ เหมือน [[project-fuel-move-0556-0560]] ทะเบียน≠คนขับ): เลขของ เรวัตร ที่เก็บไว้จริงเป็นของวัชร์นล, ของวัชร์นล เป็นของชัชวาล. แก้:
- เรวัตร(140) → SCB 345-437-1962 (เดิม 407-488-1123 ผิด)
- วัชร์นล(141) → SCB 407-488-1123 (เดิม TTB 129-229-8823 ผิด)
- ชัชวาล(142) → TTB 129-229-8823 (เดิม SCB 379-202-9318 ผิด = เลขของเสรี)
- ปรีชา(165) → กรุงไทย 702-040-1236 (เดิมว่าง)

**นามสกุล** ดึงจาก gsheet AYU 1F5eJlYsNAGi1zzm1Ej-dlk7Jcp6EEUz8cq1Om4n5VnQ ชีท "Jun 26" คอลัมน์ "ชื่อ-พขร." (โอสั่งให้ดูจาก Sheet): เรวัตร บันทะสารย์ / วัชร์นล นันทะเดช / ชัชวาล ศิริประเสริฐ (ตัด "นาย" ออก). หน้าโอนเงินโชว์ employee.full_name อยู่แล้ว แค่ data เก็บชื่อต้นล้วน.

**ป้าไก่ = ประเสริฐ สุวรรณโจ (แม่บ้าน AYU)** — คนที่ [[project-ayu-office-ss.md]] ค้างไว้ "แม่บ้านใหม่ 12,000". สร้าง emp id170 office_monthly base 12,000, ออมสิน 020-185-469-168, start 12/6, ss_exempt, **รอบจ่าย 1-31 (calendar ไม่ใช่ 26→25)**. รอบนี้ 19 วัน(12-30มิ.ย.)×400=7,600. ลง item run#18 net 7,600 (set ตรงบน item เหมือน office อื่น engine คิด office ไม่ได้).

**เรืองฤทธิ์(133)** ออกแล้ว รับเงินเดือนงวดสุดท้ายเดือนก่อน → คืนเงินประกันตน 10,000. เขาไม่มีใน run18. โอสั่ง "ลงรอบ 18 เป็นคืนล้วน net 10,000": add item run18 special_income +10,000 net 10,000 (ตรง precedent คนลาออก note "ออก+คืนปกต"), set deposit_balance→0, status inactive end 2026-05-31, +log driverdeposit −10,000. ใช้บัญชีเดิมเขา กรุงไทย 218-064-1427.

**ผล:** run18 31→33 items, net 246,193.34→263,793.34 Δ=+17,600 (=7,600+10,000) เป๊ะ; รอบอื่น 17 รอบนิ่งหมด (net_guard-style check). Verified rendered HTML จริง (/payroll/18/print in-process) ทุกชื่อ-เลขจับคู่ถูก.

GOTCHA: payrunitem มีคอลัมน์ FLOAT NOT NULL ไม่มี default เพียบ (days_leave ฯลฯ) — INSERT ต้องเติมทุกคอลัมน์ =0.0 ไม่งั้น IntegrityError. ใช้ helper เติม PRI_NUM ทั้งชุด.

**บัญชีซ้ำ แก้แล้ว:** รุ่งเรือง(138) & นิวัติ(139) เคยใช้ TTB 639-214-6418 ร่วมกัน → โอบอกรุ่งเรือง=ทหารไทย 922-907-2732, นิวัติ คงเดิม. ไม่เหลือบัญชีซ้ำในระบบ.

**DEPLOYED live 30มิ.ย. (DB-only, app.yklogistics.uk):** โอสั่ง "ขึ้น server ได้เลย". ทำตาม WAL-safe + probe-ก่อน-push:
1. **probe เทียบ local↔server ก่อน** (โอกำชับ ห้ามทับงาน session อื่น): checkpoint WAL บน server copy (app_probe.db + venv python `PRAGMA wal_checkpoint(TRUNCATE)`) แล้ว scp มา diff → **17 รอบอื่น Δ=0 เป๊ะ**, เฉพาะ run18 +17,600; emp diff เฉพาะ 6 รายการที่ตั้งใจ; main.py hash local=server (โค้ดไม่ต่าง). พิสูจน์ push DB กระทบแค่งานเรา.
2. `deploy_mvp.sh --with-db` **ล้มที่ scp DB เพราะ Windows lock (app ถือ 8010 เปิด app.db)** = bug เดิม (copy ก่อน stop) → ทำมือ: Stop-ScheduledTask YK_MVP_APP + kill 8010 by PID (8020 archiver รอด) → clear stale wal/shm → scp DB → byte+MD5 verify (server=local) → Start-ScheduledTask → 8010 up, 8020 up, /login 200, public 200.
3. verify live DB จริง: ทุกชื่อ-เลขจับคู่ถูก, run18=33 items net 263,793.34.

**GOTCHA deploy:** (a) `$env:VAR` ผ่าน bash→ssh→PS โดน bash กิน `$` → เขียนเป็น .ps1 ส่งไปรันแทน quoting hell; (b) Thai print บน server console = cp874 crash → เขียน output ลงไฟล์ UTF-8 บน server แล้ว scp กลับมาอ่าน; (c) server backup ก่อน swap: app.db.bak_predeploy_20260630_194230.

Backup local: app.db.bak_20260630_192825 (ก่อนแก้), app.db.bak_rung_* (ก่อนแก้รุ่งเรือง). กฎ gsheet: ครั้งนี้แค่ "อ่าน" Sheet ไม่ได้แก้ → ไม่ต้อง comment ([[feedback-gsheet-edit-ask-and-comment]]). Deploy flow → [[reference-deploy-mvp-selfverify]], [[reference-mvp-server-deploy]].
