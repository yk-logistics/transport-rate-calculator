---
name: project-lcb-deposit-sso-resync
description: LCB deposit (เงินประกันตน) installment sync from SSO sheet — balance = งวดที่จ่ายครบ × 1000
metadata: 
  node_type: memory
  type: project
  originSessionId: 09916d86-fbc0-4c5a-bfc8-46e13949f62c
---

LCB เงินประกันตน (deposit) sync จากไฟล์ SSO. tool: `tools/lcb_sync_deposit_sso.py` (match LCB payrun
members + first-name, idempotent, recompute ท้าย).

**ground truth = ไฟล์** `Work\Salary\2026\6.Jun\LCB\บันทึกประจำเดือน หัวลาก.xlsm` ชีท **SSO**.
โครง: col0/1=ชื่อ, **col4=งวด X**, col7=total(10), col6=ครั้งล่ะ(1000). (มีชีท per-driver เยอะใน .xlsm).

**กฎที่ถูกต้อง (แก้แล้ว 29มิ.ย. รอบ2 — โอยืนยัน):** "X/10" = **จ่ายครบแล้ว X งวด** →
set `deposit_balance = X × 1000`, `deposit_target = total × 1000`. engine หัก `min(1000, target−balance)`:
  - X=10 → balance=10000=target → **หัก 0 (จ่ายครบ)** ✓
  - X=4  → balance=4000 → หักงวดที่ 5 → สลิปโชว์ "5/10" (= งวดที่กำลังหักรอบนี้)
display filter `_fmt_dep_install` (main.py): paid=bal//1000; current = paid+1 ถ้า paid<total ไม่งั้น total.
balance=X×1000 → โชว์ตรงทั้งตอนหัก(5/10) และตอนครบ(10/10).

**บั๊กเดิมที่แก้:** รอบแรกตั้ง `(X−1)×1000` (เข้าใจผิดว่า X=งวดที่กำลังหัก) → ล่าช้า 1 งวด →
คนผ่อนครบ 10/10 (balance 9000) **ยังถูกหัก 1000 อีกงวด**. โอ flag จากรูป SSO ("10/10 ควรหัก 0").
แก้ tool บรรทัด `new_bal = gw * per`. ผล LCB draft #2: 17 balance แก้, **10 คนครบหยุดหัก**
(เนื้อ/นันทสิทธิ์/ประจัก/สุวิทย์/สุรเดช/ปกรณ์/พิชิต/สันติพงษ์/ชยุต/อภิชาติ) → net 266,058→**276,058 (+10,000)**.
net_guard: รอบอื่นไม่ขยับ. **วราวุฒิ ไม่อยู่ใน SSO** → คงเดิม balance=0 (โอสั่งให้หักงวด1 = ถูกอยู่แล้ว).

deploy `--with-db` ขึ้น server: **GOTCHA deploy_mvp.sh --with-db ยัง scp app.db ก่อน stop → lock fail**
(line 57 scp ก่อน step4 cutover). workaround: stop 8010 เอง (by PID เทียบ 8020≠8010 กัน LINE archiver ตาย —
8010 cmdline ไม่มี "YK_MVP" เพราะเป็น cwd ไม่ใช่ arg, kill by PID ตรงๆ), scp, byte-verify, Start-ScheduledTask
YK_MVP_APP. ยืนยันบน server: 10 คน install=0, 8020 รอด, public 200.

related: [[project-payroll-slip-petty-itemize]], [[project-deposit-installment-number]], [[reference-deploy-mvp-selfverify]], [[reference-deploy-via-tailscale]]
