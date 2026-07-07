# Runbook ปิดรอบเงินเดือน (ทุกไซท์) — สำหรับโมเดล/คนที่ทำรอบถัดไป

> เขียน 5 ก.ค. 2026 (Fable) กลั่นจากการปิดรอบ มิ.ย. จริงทั้ง 3 ไซท์ — รอบถัดไป:
> **LCB #3 ปิด 15 ก.ค.** / AYU 25 ก.ค. / BIGC สิ้นเดือน. ใช้คู่กับ memory ใน
> `.claude/memory/` (ลิงก์ท้ายไฟล์). **งานเงิน = โมเดลใหญ่เท่านั้น ห้าม delegate.**

## 0. กฎเหล็ก (ผิดข้อเดียว = เสียหายจริง)

1. **รอบ finalized ห้าม recompute** — recompute จะลบ items แล้วสร้างใหม่ ทำให้สดย่อยที่ล็อกไว้หาย. แก้เงินย้อนหลัง → ใช้กลไก C4 (PayAdjustment, `docs/PAY_ADJUSTMENT_RUNBOOK.md`) เท่านั้น.
2. **server = ความจริง, local DB = stale** — งานเงินทำบน server DB ตรงๆ (ssh) **ห้าม push local app.db ทับ** (เคยเกือบ revert +5,797 ของ LCB#2). ก่อนแตะให้ probe เทียบ net ทั้งกระดานก่อน.
3. **ห้ามเดา** ไซท์ / รอบ (วิ่ง vs จ่าย) / ชื่อคนขับคล้ายกัน / cross-site — เจอกำกวมให้หยุดถามโอ.
4. ทุกการแก้ DB บน server: **backup ก่อน + `net_guard.py before/after --allow <run>`** พิสูจน์ว่ารอบอื่นนิ่ง.
5. **ground truth = ไฟล์ xlsx ต้นทางของทีม ไม่ใช่ DB** — reconcile กับไฟล์เสมอ (บทเรียน: เคยเติม tfd เองแล้วต้อง revert เพราะไฟล์บอก 0).

## 1. วงรอบ + ชื่อรอบ

| ไซท์ | วงรอบวิ่ง | cycle_tag | หมายเหตุ |
|------|-----------|-----------|----------|
| LCB  | 16 → 15 เดือนถัดไป | เดือนที่จบ (16มิ.ย.–15ก.ค. = `2026-07`) | |
| AYU  | 26 → 25 เดือนถัดไป | เดือนที่จบ | |
| BIGC | 1 → สิ้นเดือน | เดือนที่วิ่ง | **ชีทเรียก "เดือน X" = วิ่งเดือน X−1** (จ่ายเดือนถัดไป) |

## 2. ก่อนปิดรอบ — checklist ตามลำดับ

รันทุกคำสั่งจากราก repo; ตัวที่แตะ server DB ให้รันบน server.

1. **เดลี่ครบรอบ** — import จบแล้ว ไม่มีเที่ยวค้าง. **AYU รอบ 2026-07 import กลางรอบไปแล้ว 6ก.ค. (314 งาน) + โอเคาะกติกา: ข้อมูล AYU แก้ที่"ชีทจริง"เท่านั้น ห้ามแก้ใน grid** → ก่อนปิดรอบ 25ก.ค. ให้ re-import สุดท้าย: export ชีทจริง (id 1F5eJlYs…) เป็น xlsx → scp ทับ `YK_MVP/tools/ayu_gsheet.xlsx` บน server → รัน `_run_ayu_import.ps1` (dry-run ดูยอด) → apply พร้อม `--wipe-prior` (ลบ source=ayu_2026-07 แล้วเขียนใหม่ทั้งก้อน — ปลอดภัยเพราะไม่มีใครแก้ grid). **ถ้าพบว่ามีใครแก้ grid AYU ไปแล้ว: ห้าม wipe เด็ดขาด** (ของหาย — ตระกูล C4) ให้เทียบมือแทน. ไซท์อื่น (LCB/BIGC) กติกาเดิม: import ครั้งเดียวตอนจบรอบ แล้วแก้ใน grid — ห้าม re-import ทับ.
2. **สดย่อย (petty) ครบ** — `import_petty_cash.py` แล้วเช็ค: คนขับใหม่ที่ onboard หลัง import ต้องดึง petty ของเขาตามมาด้วย (เคสปรีชา 4,095). คนที่ลาออกแล้วมียอดในชีท = carry ไปรอบหน้า ไม่ใช่บั๊ก (เคสวันชัย).
3. **น้ำมัน reconcile** — `python ProjectYK_System/tools/fuel_slip_reconcile.py <run_id>` ต้องไม่มี MISMATCH (กฎโอ: Σ น้ำมันในตารางสลิป = fuel_cost_self ทุกคน mao; ส่วนต่างต้องมีบรรทัด off-table). **ย้ายน้ำมันข้ามคน/รถ ต้องแก้ 2 ที่**: FuelTxn (คุมเงินหัก) + DailyJob.fuel_amount/liter แถวเดิม (คุมสลิป).
4. **preflight** — `python ProjectYK_System/tools/preflight_payrun.py --site <SITE> --run-id <id>` (read-only, JSON ลง reports/): unlinked / cycle-drift / cross-site / source scan.
5. **เทียบ ground truth ต่อไซท์** (ตัวเลขที่ต้องตรงจากรอบ มิ.ย. — โครงไฟล์เดียวกันทุกเดือน):
   - **LCB**: `วางบิล YK VOLVO.xlsx` ชีท Daily (E=คนขับ, Y=ค่าขนส่ง, AD/AF/AG=ค่าเที่ยว/พิเศษ/OT, AL=ค่าเที่ยวพขร) + petty ชีทเดือน คอลัมน์ O.
   - **BIGC**: `25xxDaily Report.xlsx` ชีทเดือน (ค่าเที่ยว J) + `เรทน้ำมันเดือนX.xlsx` ชีท `รวมเรท` — **fuel_rate_income = ลอกคอลัมน์ G ต่อหัวตรงๆ** (ติดลบได้) + `สดย่อยวังน้อย.xlsx` คอลัมน์ O.
   - **AYU**: ชีทพี่หวาน (sync ผ่าน `tools/wan_sheet_sync/`) + รูปเงินเดือน office = ground truth ฝั่ง office.
6. **Deposit (เงินประกันตน)** — งวดต้องตรงชีท; SSO format **"X/10" = จ่ายครบ X งวดแล้ว → balance = X×1000**; office ไม่หัก deposit; คนใหม่เริ่มงวดตามที่โอสั่งรายคน.
7. **KB** — LCB CY: คนขับคิดจากราคาคีย์ (kb = 5000−คีย์) ส่วนต่างเข้าบริษัท; NHL มี KbRule default 110; สูตรฐาน `driver_calc_price = (price_override ?? revenue) − kb`. preflight เฉพาะ: `preflight_kb_driver_price.py`.
8. **net_guard snapshot** — `python ProjectYK_System/tools/net_guard.py before` (บน server) ก่อนเริ่ม recompute ใดๆ.

## 3. กติกา engine ต่อโหมด (อย่าแก้โดยไม่มีเทสต์)

- **lcb_mao / ayu_mao**: จ่าย = Σ `trip_fee_driver` ต่อเที่ยว (honor override มือ) **− KB-share เฉพาะแถวที่ tfd>0** — ไม่ใช่ revenue×60% รวมรอบ. แถว rev>0 แต่ tfd=0 = "ยังไม่ลงค่าเที่ยว" อย่าเติมเอง (ตามไฟล์เท่านั้น).
- **lcb_mixed**: วันเที่ยวได้ค่าเที่ยว + วันเหมาคิด 60%(rev−KB); วันหักน้ำมัน = วันเหมา + วันจอดช่วงเหมา (`_classify_lcb_days`).
- **BIGC**: บริษัทออกน้ำมัน (fuel_self=0) → รายได้คิดภาษีสูงกว่าไซท์อื่น = ไม่ใช่บั๊ก (เรื่องภาษีรอโอตัดสิน); วันหยุด/อนุโลมตาม memory bigc-holiday-anuloom.
- **หน้าโอนเงิน**: ยอดเตรียมโอน = Σ net เฉพาะ **net > 0** (คนติดลบ = หนี้บริษัท ห้ามเอามาหักยอดรวม).
- เทสต์เงินคุ้มกันทั้งหมด ~55 ตัว (test_money_rules_2, test_lcb_pay_modes, test_ayu_pay_modes, test_pay_adjustment, ฯลฯ) — **แก้ engine แล้วต้องรัน pytest เต็มก่อน deploy.**

## 4. Recompute อย่างปลอดภัย

- recompute ได้เฉพาะรอบ **draft** ที่เดลี่ครบ+tfd ครบ (รอบเก่าที่ importer ไม่ลง tfd → recompute = เงินหาย).
- **GOTCHA office copy (AYU)**: recompute ทั้งรอบจะล้างรายการ office ที่ copy มา — ถ้าแก้เฉพาะบางคนให้ใช้ท่า `calc_one_employee` ทับ item รายคน (ดู `tools/ayu_mao_recompute_run18.py` เป็นแบบ) แทน compute ทั้งรอบ; ถ้าจำเป็นต้องทั้งรอบ → re-copy office ตาม memory ayu-jun-payroll.
- หลังทุกครั้ง: `net_guard.py after --allow <run_id>` — รอบอื่นขยับ = หยุด สอบสวนก่อน.

## 5. Finalize

- ปุ่ม finalize มี gate: `cycle_drift` (petty tag ตรงรอบแต่วันที่นอกช่วง — มักเป็นเบิกล่วงหน้า/หนี้เก่าที่ทีมตั้งใจ) และ `policy_review` (แท็กไม่ตรง policy). **เจอ gate → ตรวจว่าเป็นยอดที่ทีมตั้งใจหักจริงก่อน แล้วให้โอเคาะ** — force ได้เฉพาะโอสั่ง (ทำครบขั้นตอนเดียวกับปุ่ม: status + finalized_at + lock petty + note).
- finalize แล้ว: แก้ราคา/ค่าเที่ยวย้อนหลังผ่าน grid ได้เลย → ระบบตั้ง PayAdjustment ให้อัตโนมัติ ไปบวก/หักรอบถัดไป (C4, idempotent, ยกเลิกได้ก่อนถูกดูด).

## 6. หลังปิด — สลิป/เอกสาร

- สลิป 3 surface: รายคน+ZIP = `payroll_slip.html`, /print = `payroll_print_all.html`, ตารางใน `_slip_body.html` — **แก้ CSS ต้องแก้คู่ทั้ง 2 surface เสมอ**. ZIP ทำ PDF ฝั่ง server ด้วย Chrome (ไทยคมชัด).
- ชุดผู้บริหาร (`?for=boss` / ZIP for=boss) มีคอลัมน์ KB/ค่าขนส่งจริง + **ธงน้ำมันผิดปกติ ⚠** (เติมถี่≥3บิล/วัน, เกินถัง, เติมวันไม่มีงาน) — สลิปคนขับไม่มีธง.
- ก่อนแจก: `fuel_slip_reconcile.py` ผ่าน + สุ่มเทียบสลิปกับไฟล์ต้นทาง 2-3 คน (โดยเฉพาะคนที่มี handover/วัดถัง/ยกยอด).
- KB payout (จ่ายเจ้าของงาน CY): หน้า `/kb-payout` + `docs/KB_PAYOUT_RUNBOOK.md`.

## 7. เครื่องมือหลัก (ทั้งหมดใน `ProjectYK_System/tools/`)

| เครื่องมือ | ใช้ทำอะไร |
|-----------|-----------|
| `net_guard.py before/after --allow <ids>` | พิสูจน์รอบอื่นนิ่งทุกครั้งที่แตะเงิน |
| `preflight_payrun.py --site X --run-id N` | ตรวจ 4 มิติก่อนปิด (read-only) |
| `fuel_slip_reconcile.py <run_id>` | น้ำมัน mao ตาราง=หักจริง |
| `preflight_kb_driver_price.py` | KB ↔ ราคาคีย์ |
| `import_lcb_daily.py --cycle 2026-07 --dry-run` | **เดลี่ LCB (ใหม่ 7ก.ค. — parameterized, พิสูจน์เลขตรงสคริปต์เดิมเป๊ะ)**: ไฟล์ = `Salary/2026/7.Jul/LCB/วางบิล YK VOLVO.xlsx` (Excel local โอ = source of truth); dry-run ดูยอดก่อน แล้วค่อยรันจริง (`--wipe-prior` ถ้าเคย import รอบนี้แล้ว); override ไฟล์ด้วย `--xlsx` |
| `import_bigc_daily.py` (cycle 2026-06 เตรียมแล้ว) | เดลี่ BigC วิ่ง มิ.ย. — รอไฟล์ `7.Jul/BigC/` จากทีม |
| `import_ayu_daily.py --cycle 2026-07` | เดลี่ AYU — ดูขั้น re-import จากชีทจริงใน §2 ข้อ 1 |
| `deploy_mvp.sh --markers "<ascii>"` | deploy + self-verify (marker สแกน main.py+templates+services แล้ว — ซ่อม 5ก.ค.) |

**Deploy DB ขึ้น server**: ห้าม scp app.db ดิบ (WAL → malformed) — ใช้ backup-API + `wal_checkpoint(TRUNCATE)` ก่อน + swap ตอน 8010 หยุด (kill by PID เท่านั้น อย่า filter .venv — โดน LINE archiver 8020). และ **swap DB ต้อง preserve appuser hash จาก server ก่อน** (ไม่งั้นรหัสทีมหาย — memory mvp-password-db-swap-gotcha).

## 8. Memory ที่ต้องอ่านเมื่อเจอเคสเฉพาะ

- ปิดรอบ มิ.ย. ทั้งหมด: `project-jun-close-3sites`, `project-lcb-bigc-jun-payroll-review`
- โหมดจ่าย: `project-lcb-mao-pertrip-pay`, `project-ayu-mao-pertrip-pay`, `project-lcb-mixed-mode`, `project-bigc-may-payroll`
- KB: `project-lcb-cy-kb-fulls`, `project-kb-driver-calc-price`
- Deposit: `project-deposit-installment-number`, `project-lcb-deposit-sso-resync`
- น้ำมัน: `feedback-slip-fuel-must-reconcile`, `project-mao-fuel-tank-measure`, `project-fuel-exclude-from-driver`
- สลิป: `project-slip-surfaces-consistency`, `project-slip-fuel-fill-date`, `project-slip-ktag-mixed-table`
- แก้ย้อนหลัง: `project-c4-pay-adjustment` + `docs/PAY_ADJUSTMENT_RUNBOOK.md`
