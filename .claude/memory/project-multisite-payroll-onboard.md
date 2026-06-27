---
name: project-multisite-payroll-onboard
description: Night-run 2026-06-27 onboarded BIGC+AYU by copying bank-sheet net (not engine calc); LCB reconciled to actual pay; COPY-LOCK guard; รถร่วม still TODO
metadata: 
  node_type: memory
  type: project
  originSessionId: 91ddce0a-48bd-4312-affe-febfb58477d1
---

Night run 2026-06-27→28 (โอ unlocked money fully, ran overnight unattended). Branch `night-run/ground-truth-payroll-2026-06-27`, 6 commits.

**ANCHOR rule (โอ-confirmed):** ชีทโอนเงินเดือน / แบงค์.pdf = เงินโอนเข้าบัญชีจริง = ground truth สูงสุด. ลำดับ: ชีทโอน > PDF สลิป > Daily Excel. ไฟล์ขัดกัน → ใช้ rev.1/ใหม่กว่า.

**ผลลัพธ์ (DB state):**
- LCB #1 พ.ค. finalized 378,939 (ตรงเงินจ่ายจริงทุกคน — เวอร์ชันแก้ "ตกหล่นค่าเที่ยววิชาญ"→วิชาญ 13,532). #2 มิ.ย. draft 257,497 (recompute fresh; petty ตรงสดย่อย col O 18/18; fuel เหมาตรง FuelTxn).
- BIGC onboard ใหม่ 11 คน (id 103-113, pay_mode bigc_monthly). #3 เม.ย. 118,137 + #4 พ.ค. 110,614 — **ลอก net จาก Book1 ชีท "รวม YK"** (โอคำนวณมือ).
- AYU onboard ใหม่ 31 คน (id 114-144; 12 office incl โอ+ครอบครัว + 19 คนขับ). #5 พ.ค. 267,117 — **ลอกจากแบงค์ AYU rev.1.pdf**. 2-ระบบ: ชัชวาล→เที่ยว 6,107; รุ่งเรือง→0(ติดลบ). net=0 flag: สุริยันต์/รุ่งเรือง/ธัชชนพล.

**Why ลอกยอดแทน engine:** BIGC base salary (1,800-9,000/คน) + route→rate table **ไม่มีเขียนไว้**; AYU 2-ระบบ + เรทน้ำมัน → engine เดาไม่ได้ = เสี่ยงผิดทั้งไซท์. ลอก net จริงแทน = ตรง 100% แต่ engine ยังคำนวณ BIGC/AYU เองไม่ได้ (รอ โอ ให้สูตร).

**COPY-LOCK guard:** payrun ที่ notes ขึ้นต้น `[COPY-LOCK]` (BIGC #3,#4 + AYU #5) → recompute route เด้ง `?err=copylock` กัน engine ทับยอดลอก. LCB ไม่ tag (engine คำนวณได้จริง). อย่าเอา COPY-LOCK ออกจน BIGC/AYU มีสูตร engine ครบ.

**ยังค้าง (โอต้องตัดสิน):** [[project-rojruam-bunnam-todo]] รถร่วม; สูตร engine BIGC/AYU; AYU นิวัติ rev.1 9,159 vs แบงค์ 7,788 (ต่าง 1,371, ใช้แบงค์).

ground truth files: docs/ground-truth/{lcb_truth.csv, bigc_ruamyk.csv, ayu_paid.csv, *_survey.md, MORNING_REPORT.md}. onboard scripts: tools/onboard_{bigc_from_ruamyk,ayu_from_paid}.py (idempotent, wipe+recreate per-site).
