# Night Run — Ground Truth Payroll (2026-06-27)

**Branch:** `night-run/ground-truth-payroll-2026-06-27` (from HEAD, NOT origin/main — needs current DB+memory state)
**Operator:** Claude (Opus 4.8, effort max) = brain/money-decisions · Sub-agents (Sonnet) = bulk reads/scripts/draft code
**Authorized by โอ 2026-06-27 ~21:37:** money fully unlocked, run all phases overnight, no stopping, decide on his behalf when blocked, deploy to prod if tests pass.

## North Star (โอ's dream)
ตื่นมาเห็นระบบที่ reconcile กับเงินจ่ายจริง 6 เดือน, draft รอบใหม่พร้อมกด finalize, รายงานเช้าบอกทุกอย่าง.

## THE ANCHOR (most important rule)
**ชีทโอนเงินเดือน = ground truth สูงสุด** — `สรุปเงินเบิกแหลม*.xlsx` (LCB) + `แบ็งค์.pdf` / `BANK.pdf` (ทุกไซท์).
เพราะมันคือ "เงินที่โอนเข้าบัญชีคนขับจริง" = สะท้อนการตัดสินใจของโอไปแล้ว (เลือกเที่ยว vs เหมา, จ่ายพิเศษ ฯลฯ).
ลำดับความเชื่อถือ: **ชีทโอน > PDF สลิป > Daily Excel**. ไฟล์ขัดกัน → ใช้ไฟล์วันที่ใหม่กว่า + จดไว้.

## Decision rules (เมื่อ blocked, ห้ามหยุดรอ)
1. ตัดสินใจแทนโอด้วยกฎ ANCHOR ข้างบน → match ยอดชีทโอน → จดใน MORNING_REPORT ว่าตัดสินอะไร+เหตุผล.
2. AYU เคส "2 ระบบ (เที่ยว/เหมา)": บางคนบริษัทยอมจ่ายตัวมากกว่า, บางคนน้อยกว่านิดหน่อยจ่ายแบบเดิม → **ยอดในชีทโอนคือคำตอบ** (มันบันทึกว่าโอเลือกอะไรไปแล้ว). match ตามนั้น.
3. ไฟล์อ่านไม่ได้ (.xls เก่า/.xlsm/PDF สแกน) → แปลงให้สุดความสามารถ (LibreOffice headless convert, OCR). จริงๆ ไม่ได้ค่อยจด BLOCKED.
4. ผ่าน test → deploy prod (app.yklogistics) ตาม runbook (backup app.db + stop + scp DB/code + restart task). ดู memory: reference-mvp-server-deploy, reference-mvp-deploy-restart-gotcha.

## Current system state (snapshot 2026-06-27)
- DB `ProjectYK_System/app/app.db`, SCHEMA_VERSION=27.
- payrun #1: LCB 2026-05 (04-16→05-15) **finalized** net 378,939 / 21 items.
- payrun #2: LCB 2026-06 (05-16→06-15) **draft** net 256,943 / 18 items.
- BIGC / AYU / รถร่วม: **ยังไม่เข้าระบบเลย** — ground truth ครบใน Salary/2026 ตั้งแต่ ม.ค.
- engine: services/payroll.py — pay modes incl lcb_mao/lcb_trip/lcb_mixed, driver_calc_price (rev−KB), tax withholding, finalize-lock with `force=` param. compute_pay_run(session, pay_run, recompute=True, force=False).
- pay cycles: BIGC 1→สิ้นเดือน (tag YYYY-MM) · LCB 16→15 (tag=เดือนจบ) · AYU 26→25 (tag=เดือนจบ).

## Ground truth file map (Salary/2026)
Root: `C:/Users/guole/Desktop/2026.5.28/Desktop/Work/Salary/2026/{1.Jan..6.Jun}/{AYU,BigC,LCB,รถร่วม}/`
- ชีทโอน LCB: `สรุปเงินเบิกแหลม <range>.xlsx` (มี ม.ค.-มิ.ย., มิ.ย.=16-05-15-06).
- ชีทโอนทุกไซท์: `แบ็งค์.pdf` / `BANK.pdf`.
- สลิปต่อคน: `<ชื่อ>.pdf` (LCB/BigC/AYU folders).
- เรทน้ำมัน: `เรทน้ำมันเดือน*.xlsx` (BigC).
- Daily: `Daily Report*.xlsx`, `Daily แหลมฉบัง2*.xlsx`, `สดย่อยวังน้อย*.xlsx`.
- วางบิล: `วางบิล YK VOLVO*.xlsx` (LCB).
- หลักฐาน conflict: `5.May/LCB/LCB ตกหล่นค่าเที่ยวิชาญ.pdf` = เวอร์ชันแก้ของ พ.ค. (ใหม่กว่า LCB.pdf → ถือเป็นจริง).

## Phases (run sequentially, no waiting)
0. **Extract** (sub-agent): อ่าน ground truth → CSV `docs/ground-truth/<site>_truth.csv` (emp|month|net_transferred|account_no|breakdown). flag conflicts.
1. **Reconcile** (main): ชีทโอน vs payrunitem ทีละคน → `docs/ground-truth/<site>_reconcile.md` (ตรง/Δ/สาเหตุ).
2. **Fix+draft** (TDD on branch): test reproduce → fix payroll.py → recompute ให้ตรงชีทโอน. commit ทีละ fix.
3. **Next sites**: BIGC→AYU→รถร่วม, วน 0-2. import ผ่าน tools/import_*.py หรือเขียนใหม่ตาม pattern. AYU 2-ระบบใช้ ANCHOR.
4. **Morning**: `docs/ground-truth/MORNING_REPORT.md` + deploy(ถ้าผ่าน) + update memory.

## Safety
- branch แยกแล้ว (ไม่ใช่ main). backup app.db ก่อนแตะ DB ทุกครั้ง: `app.db.bak_nightrun_<phase>_<ts>`.
- finalize: โอกดเอง (เตรียม draft ให้พร้อม). แต่ "แก้ยอดให้ตรงชีทโอน" = อนุมัติแล้ว (ข้อมูลทดลอง).
- ทุก money-touching change ต้องมี test + ระบุวิธีตรวจย้อนกลับ.

## Wake clock
21:37 start. window reset 22:00 → นับรอบ 5h ใหม่. ชน limit → auto-resume (memory: reference-auto-resume-system). resume แล้วอ่าน spec นี้ + TaskList + ไฟล์ใน docs/ground-truth/ ล่าสุด เพื่อรู้ว่าทำถึงไหน.
