# NEXT ACTION PLAN

แผนงานลำดับถัดไป (เรียงตามความสำคัญ)

## ⭐ Quick Status (2026-05-08 | Token context — ประหยัด Conversation + ไฟล์ที่โตใน repo)

- [done] เพิ่มกฎ `.cursor/rules/exec-brief-noncoder.mdc` (ตอบสั้น ภาษาคน ไม่อธิบายโค้ดโดยดีฟอลต์) คู่กับกฎเงิน/ข้อมูลเดิม
- [done] เพิ่มเอกสาร `ProjectYK_System/docs/CONTEXT_TOKENS.md`, `CHANGELOG_POLICY.md`, `CHANGELOG_ARCHIVE.md`, `DOMAIN_AND_DIRECTION.md` และอัปเดต bootstrap / `AI_CURSOR_CLAUDE_WORKFLOW.md` / `MODULE_REGISTRY.md`
- [next] เมื่อ `CHANGELOG_MASTER.md` ยาวเกินประมาณ 800–1000 บรรทัด — ย้ายช่วงเก่าไป `ProjectYK_System/docs/CHANGELOG_ARCHIVE/*.md` ตามนโยบายใน `CHANGELOG_POLICY.md`
- [next] ให้โอเติม `ProjectYK_System/docs/DOMAIN_AND_DIRECTION.md` เมื่อมีบริบทบริษัท/ทิศทางยาวๆ (ไม่ต้องพิมพ์ซ้ำในแชต)

## ⭐ Quick Status (2026-05-07 | Forward Insight benchmark -> One Platform UX uplift)

- [done] Oatside monetary formatting 2dp end-to-end: ปรับ `build_oatside_reports.py` ให้แสดงผลเงิน 2 ตำแหน่งใน HTML/XLSX/CSV, rerun build, verify คอลัมน์หลัก (`Trip_rate_baht`, `Downtime_50_baht`, `Downtime_100_baht`, `Blank_run_50_baht`, `Return_job_baht`), และ deploy publish commit `4d203ab`\n- [next] ตรวจหน้า live แบบ cache-bypass และสุ่มยืนยัน 2dp บน `index/trips/plate` อีก 1 รอบก่อนส่งลูกค้า\n- [done] สำรวจระบบตัวอย่างแบบลงหน้าใช้งานจริง: เมนูหลักครบ (`ขนส่ง/จัดซื้อ/บัญชี/บุคคล/ตั้งค่า`) + หน้ารายการ `Trip`, `Expense`, `Payroll` และหน้า detail เที่ยว
- [done] สกัด pattern ที่นำกลับมาใช้ได้ทันที: mega-menu รวมเมนูย่อย, action bar ระดับรายการ, workflow status เดียวข้ามโมดูล, table + filter หนาแน่นพร้อม export/report
- [done] สร้าง checklist ปิดงานเมนู demo: `TransportRateCalculator/docs/FORWARD_INSIGHT_MENU_CHECKLIST.md` (สถานะ `[done]/[partial]/[todo]`)
- [done] ปิดหมวด `การจัดซื้อ` ใน checklist ครบทุกหน้า (รอ loading overlay ก่อนคลิกทุกครั้ง): `expense`, `expense-item`, `stock`, `refuel`, `fuel-card`, `fuel-station`
- [done] ปิดหมวดย่อยบัญชีเพิ่ม 4 หน้า: `tms-document`, `bill_income`, `invoice_income`, `payment_income` (ยืนยันด้วยกติกา wait overlay ทุกคลิก)
- [done] ปิดเพิ่มฝั่งบัญชีอีก 3 หน้า (`bill_pay`, `invoice_pay`, `payment_pay`) และฝั่งบุคคลอีก 3 หน้า (`saving`, `income-type`, `income-package`)
- [done] ปิดหมวดบุคคลครบทั้งหมวดแล้ว (เพิ่ม `sso`, `taxandInsurance`, `dashboard/document`, `hr/employee`, `tms/site`, `hr/department`, `hr/title`)
- [done] ปิดเพิ่มฝั่งบัญชีอีก 3 หน้า (`รายการเที่ยววิ่ง`, `สรุปรายการค่าขนส่ง`, `แบ่งชำระ`) ด้วย URL `account/carrier/invoice`, `account/carrier/bill`, `account/carrier/finance`
- [done] ปิดหมวด `บัญชี` ที่เหลือครบแล้ว (เพิ่ม `expense`, `adjusting_entries`, กลุ่ม `monthly_wht/vat/tax/journal/chart/gl/tb/pnl`)
- [done] ปิดหมวด `ตั้งค่า` เพิ่มอีก 5 หน้า (`partner`, `settinginvoice`, `excel`, `core/product`, `core/product-category`)
- [done] ปิดหมวด `ตั้งค่า` ที่เหลือครบแล้ว (`uom`, `core/vehicle`, `core/vehicle-model`, `core/vehicle-type`, `core/vehicle-brand`, `core/vehicle-energy`)
- [done] ปิดหมวด `ขนส่ง` เพิ่มอีก 4 หน้า (`tms/report/amount_trip`, `tms/product`, `tms/product-type`, `tms/place`)
- [done] ปิดหมวด `ขนส่ง` ที่เหลือครบแล้ว (`tms/vehicle`, `tms/run-type`, `tms/pay-type`, `tms/extra`) ทำให้ checklist demo ครบ 100%
- [done] **Wave 1 Guardrail #1** — `site_from_requester()` ใน `alias_map.py` + `import_petty_cash.py` pre-assign `site_code` จาก requester suffix ตอน insert (BigC 205 rows, AYU 71, LCB 23 ที่จะ fix ในรอบ re-import ถัดไป)
- [done] เพิ่มแนวทาง **Claude Code Lean Mode** ลด token: อัปเดต `AI_CURSOR_CLAUDE_WORKFLOW.md` + `CLAUDE.md` และเพิ่ม `docs/CLAUDE_CODE_LEAN_PROMPT_TEMPLATE.md`
- [done] เพิ่ม **Ultra-Lean 5 lines** + snippet ไฟล์พร้อม copy จากเทอร์มินัล (`tools/CC_LEAN_START.txt`, `tools/CC_ULTRA_LEAN_5LINES.txt`)
- [done] เพิ่ม `tools/CC_BENCHMARK_LOG.md` สำหรับจดผล 3 ตัวชี้วัด และล็อก default ทีม: งานเล็กเริ่ม Ultra-Lean ก่อน
- [done] เพิ่ม Daily Guardrails checklist ใช้งานจริง: `docs/CURSOR_CLAUDE_DAILY_GUARDRAILS_CHECKLIST_TH.md`
- [done] เพิ่ม Performance checklist รอบแรก: `docs/PERFORMANCE_FIRST_PASS_CHECKLIST_TH.md`
- [done] เพิ่ม template backup ความรู้แชตแบบ copy-paste: `tools/CHAT_KNOWLEDGE_BACKUP_TEMPLATE_TH.md`
- [done] แก้ `.cursor` sessionStart hook ให้ทำงานเสถียรบน Windows: ปรับ `cursor-digest.ps1` ให้ retry ได้หลัง network fail และ emit stdout JSON เสมอ + เพิ่ม timeout `hooks.json` เป็น 20 วินาที
- [done] **Wave 1 Guardrail #2** — saved filter preset ต่อหน้า: `BigC เดือนนี้`, `รออนุมัติ`, `ยังไม่ผูก` ใช้งานจริงแล้วใน `petty_list.html` / `daily_list.html` / `payroll_list.html` (URL query string, ไม่เพิ่ม DB)
- [done] เพิ่ม filter หน้า `/payroll` (`site/cycle/status`) + row action bar (`ดู | รอหัก | ยังไม่ผูก`) เพื่อเข้า queue รายรอบได้คลิกเดียว
- [done] อัปเกรด `preflight_payrun.py` เป็น manager-friendly: เพิ่ม `manager_summary` (pending รวม + %share ความเสี่ยง) และ morning note ส่วน `Executive summary`
- [done] **BigC cycle mapping audit/tool (recheck run)** — รันตรวจซ้ำเดือนจ่ายเม.ย.2026 ด้วย `cycle_tag=2026-03` และไฟล์ manual ชุดเดิม (`2564Daily Report (04.21).xlsx`, `Book1.xlsx`, `เรทน้ำมันเดือนมีนาคม69.xlsx`, `สดย่อยวังน้อย.xlsx`) ออกรายงาน `reports/audit_bigc_2026-03_recheck_mminus1/`
- [done] **BigC preflight gate harden (phase warning)** — เพิ่ม guardrail บนหน้า `/payroll/{run_id}`: แสดง `cycle-date drift` เป็นจำนวนรายการ + ยอดเงินกระทบทันที เมื่อพบ `pay_cycle_tag` รอบนั้นแต่ `txn_date` อยู่นอกช่วงเดือนวิ่ง
- [done] **BigC preflight gate harden (phase block)** — `POST /payroll/{run_id}/finalize` บล็อกทันทีเมื่อ `site=BIGC` และ `cycle-date drift > 0` พร้อมเขียน unresolved report ลง `reports/payroll_unresolved_queue/`
- [done] **Safe skip + unresolved queue (audit tool)** — `audit_bigc_manual_vs_system.py` ส่งออก `unresolved_queue.json/.csv` สำหรับชื่อที่ไม่ match/กำกวม และไม่ทำให้รอบ audit ล่มทั้งก้อน
- [done] **BigC unresolved safe reduce (pass 1)** — เพิ่มกฎ auto-resolve แบบพิสูจน์ได้เท่านั้น (single-prefix unique) + next action รายคนใน queue; rerun แล้ว unresolved ลด `8 -> 7` และ `missing_in_manual 1 -> 0`
- [done] **LCB preflight readonly + morning queue** — `tools/preflight_payrun.py` + รายงาน `reports/preflight_payrun_*.json` และ `reports/preflight_morning_queue/PENDING_MORNING_preflight_*.md` เมื่อเจอ HIGH
- [done] **LCB finalize drift parity** — `finalize` บล็อกเมื่อ cycle-date drift > 0 (`lcb_cycle_date_drift_block`) + refactor `_cycle_drift_predicates_for_payrun()`
- [done] **Night handoff pack (เช้า) ล่าสุด** — รวม checklist 10 นาที + outstanding queue (`BigC -> LCB -> AYU`) + critical decisions pending + 3 คำสั่งรันจริงที่ `docs/NIGHT_HANDOFF_PACK_LATEST_TH.md`
- [done] **AYU preflight hardening (end-to-end)** — เพิ่ม safe skip queue (`unresolved_preflight_*.json/.csv`) + quick-win queue (`quickwin_preflight_*.json`) ใน `reports/preflight_unresolved_queue/` (คง policy finalize ของ AYU แยกจาก BIGC/LCB)
- [done] ทดสอบ `/payroll/{run_id}/finalize` เคส drift จริง 2 รอบติดผ่าน `TestClient` — BIGC/LCB ได้ `err=cycle_drift_block` ตามนโยบาย และ AYU ยังได้ `err=unlinked_pending` ตาม policy เดิม
- [done] **Night Long-Run Coordinator (5 รอบ UX guardrail)** — `/payroll/{id}` แถบ Ops (สดย่อย/เดลี่/น้ำมัน/บิล/preflight cmd), `/payroll/.../employee/...` ลัดสดย่อยรายคน, preset เดือนนี้ที่ `/fuel` + `/billing`; verify `py_compile` + `run_payroll_test` + preflight BIGC/LCB/AYU
- [done] **Night Autopilot loop x4 (BigC->LCB->AYU->handoff)** — รัน preflight ครบ 4 รอบติดแบบไม่เดา/skip-safe, ยืนยัน risk คงที่ (`BIGC drift 7/4,150`, `LCB drift 23/14,616`, `AYU drift 33/24,430`, ทุกไซต์ unlinked `33/23,716`) และอัปเดต morning queue ล่าสุดครบ
- [next] AYU run 7: เคลียร์ unresolved 33 รายการ (23,716 บาท) ตาม `reports/preflight_unresolved_queue/unresolved_preflight_AYU_2026-03_run7.json` แล้ว rerun preflight เพื่อลด `cycle-date drift` และปลด finalize block
- [done] **Plan C (cycle policy-first)** — เพิ่ม `Employee.pay_cycle_policy` + ฟอร์มตั้งค่าทันที, เปลี่ยนคำนวณแท็กรอบในเส้นทางสดย่อย/preflight เป็น driver-policy-first (fallback site_default), เพิ่มคิว review policy และ finalize gate `policy_review_block` กันเงินตกหล่นเงียบ
- [next] ทำ data cleanup รอบแรก: ตั้งค่า `pay_cycle_policy` ให้คนขับที่ไม่ใช้ default (`cut_26_25` / `cut_16_15` / `calendar_m1`) แล้วไล่คิว `?review=1` ใน `/petty-cash` ให้เหลือศูนย์ก่อน finalize
- [next] **Cross-site collision deep check (BigC)** — ตรวจเชิงลึก 6 คนที่มีงานข้ามไซต์ในช่วงเดือนมี.ค.2026 ว่ามีผลเข้ายอด BIGC จริงหรือเป็นประวัติประกอบ เพื่อปิดความเสี่ยงปนไซต์เงียบ ๆ
- [next] **BigC audit residual cleanup (3 drivers)** — ปิด mismatch คงเหลือรายคน (`สมพร BIG-C`, `สมประสงค์`, `พรศักดิ์`) โดยยืนยัน rule รายการ `petty/fuel/trip` แล้ว rerun audit ให้ net_diff เข้าใกล้ศูนย์
- [next] **BigC manual-net rule lock (สมพร)** — ยืนยันว่าค่า net ที่ถือเป็น “ยอดจ่ายจริง” ใน `Book1` ใช้ช่องไหนเป็นแหล่งจริง (แถว `ยอดรับหลังหักค่าใช้จ่าย` vs จุดสรุปอื่นในชีท) เพื่อปิด residual `net_diff` ที่ยังเหลือ
- [done] **BigC residual close-out (pass 2)** — ปิด `พรศักดิ์ trip +1,300.00` ด้วย surgical fix แถวซ้ำ `DailyJob.id=5211` (`source=bigc_fuel_rate`, ตั้ง `trip_fee_driver=0`) + recompute `run_id=10`; rerun audit แล้ว `trip_fee_diff_total` เหลือ `0.00`
- [next] **BigC residual close-out (pass 3)** — `สมพร net -9,999.99` ยังค้างแบบ safe-by-default: ต้องยืนยันนิยาม net ในชีท manual ว่าจะถือ `ยอดรับหลังหักค่าใช้จ่าย` (ที่รวมผลจาก `เงินประกันตน=-10000`) หรือยึด net ระบบเป็นมาตรฐานก่อน finalize
- [next] **BigC unresolved queue pass 2 (เหลือ 7 คน)** — ยืนยัน master/alias รายคน (`แบ็งค์`, `ใหม่`, `อภิรักษ์`, `ไวพจน์`, `ธีระวัฒน์`, `สุพนธ์`, `นันทวัฒน์`) แล้ว rerun audit เพื่อกด unresolved ลงต่อ
- [next] ทดลองใช้งาน Lean template จริง 3 งานติด แล้วเทียบ token/time ก่อน-หลัง (ถ้าเสี่ยงตกหล่นค่อยสลับโหมดรอบคอบ)
- [next] บันทึก benchmark ลง `tools/CC_BENCHMARK_LOG.md` อย่างน้อย 3 run แล้วตัดสินใจยืนยัน default mode จากข้อมูลจริง
- [next] ทดลอง Daily Operation Pack จริง 1 วันทำงาน แล้วจดผลใน `tools/CC_BENCHMARK_LOG.md` และ backup ด้วย `tools/CHAT_KNOWLEDGE_BACKUP_TEMPLATE_TH.md`
- [next] ทดสอบ skills ภายนอกแบบจำกัด (เริ่ม profile ต่ำสุดเท่านั้น) กับงาน non-critical 1 งาน แล้ววัดผลเทียบ Lean baseline ก่อนตัดสินใจใช้งานถาวร
- [next] ทำ UI guardrail ชุดที่เหลือ (เรียง `BigC -> LCB -> AYU`): 
  1) สถานะมาตรฐานเดียว `ร่าง/กำลังดำเนินการ/รอชำระ/ชำระแล้ว`
  3) ~~action bar ในหน้า detail~~ → [done] หน้า `payroll_detail` + `payroll_employee_detail` + preset `/fuel` `/billing` (2026-05-08 night run)
- [next] ออกแบบ key-link ระหว่าง `DailyJob/PettyCashTxn/PayRunItem` ให้ drill-down ข้ามหน้าได้แบบคลิกเดียว
- [next] ตรวจพฤติกรรม hook จริงใน Cursor 1 รอบ (เปิดแชตใหม่) และยืนยันว่ามีบรรทัดล่าสุดใน `.cursor/.cache/cursor-digest.log` ตามคาด

## ⭐ Quick Status (2026-05-07 | BDT customer communication on service scope)

- [done] สรุป wording ฝั่งธุรกิจสำหรับสื่อสารลูกค้า: เหตุผลข้อจำกัดช่วงระยะ **200-600 กม.** (ต้นทุนต่อกม.เพิ่ม แต่ราคาไม่ปรับตามระยะ)
- [next] ทำ template อีเมลมาตรฐาน 2 ทางเลือก (ลดเหลือ 2 คันหลัก + รถเสริม / ยกเลิกทั้งหมด) สำหรับใช้ซ้ำเวลาเจรจา SLA กับลูกค้าประเภท BDT

## ⭐ Quick Status (2026-05-05 | Claude Code onboarding)

- [done] **`CLAUDE.md`** ที่ราก repo — คู่มือ CC: บริบท YK, อ่านก่อนลงมือ, กฎเงิน, HANDOFF ↔ `AI_CURSOR_CLAUDE_WORKFLOW.md`, ประหยัดโทเค็น, เฟสอ้างอิง (ไม่ต้องทำ Gantt Accounting SaaS แบบในเน็ตทั้งก้อน)
- [next] เปิด Claude Code จากราก `Project YK` → ทดลองเซสชันสั้น 1 scope → วางบล็อก HANDOFF จาก Cursor เมื่อต้องส่งต่อ

## ⭐ Quick Status (2026-05-06 | Vibecoding Prompt Pack ครบ 3 ไซท์)

- [done] เพิ่ม **`ProjectYK_System/TransportRateCalculator/docs/CLAUDE_CODE_VIBECODING_PLAYBOOK.md`**: playbook ใช้งานจริงสำหรับ `BigC -> LCB -> AYU` พร้อม preflight 4 checks, DoD, token-saving rules, และ prompt อังกฤษ copy-ready
- [done] อัปเดต **`ProjectYK_System/AI_CURSOR_CLAUDE_WORKFLOW.md`**: เพิ่ม “Prompt mode สำหรับโอ (Vibecoding)” ให้ Cursor สรุป prompt อังกฤษแบบคุมความเสี่ยงข้อมูลเงิน + บังคับ recompute before/after
- [next] ใช้ prompt pack นี้กับงานตรวจความถูกต้องรอบแรกของระบบเงินเดือน/นำเข้า (เริ่ม BigC ก่อน) และเก็บ baseline ตัวเลข before/after
- [next] เพิ่มเอกสาร baseline verification ต่อไซต์ (query/checklist ที่รันซ้ำรายเดือน) เพื่อปิดความเสี่ยง “คำนวณผิดเงียบๆ”

## ⭐ Quick Status (2026-05-06 | CC Auto Two-Agent Loop)

- [done] เพิ่ม runbook **`ProjectYK_System/TransportRateCalculator/docs/CC_AUTO_TWO_AGENT_RUNBOOK.md`** สำหรับรัน Claude Code แบบ 2 บทบาท (Coordinator/Executor) ด้วย 2 terminal ใน Cursor
- [done] ล็อกมาตรฐาน Task Card + Handoff Snapshot เพื่อสลับ session ถี่ๆ ตามข้อจำกัด token/hour ได้โดยไม่หลุดบริบท
- [next] ทดลองจริง 1 cycle ที่ BigC (`read-only preflight -> single-scope fix -> recompute -> quality gate`) แล้วบันทึก prompt ที่เวิร์คใน section `Working Prompts`

## ⭐ Quick Status (2026-05-06 | BigC Manual-vs-System Audit Script)

- [done] สร้าง `ProjectYK_System/tools/audit_bigc_manual_vs_system.py` เทียบไฟล์ manual baseline กับ DB (`PayRunItem`) สำหรับ BIGC รอบ `2026-03`
- [done] output หลักเป็น `JSON` + สรุปบนจอ (`reports/audit_bigc_2026-03/summary.json`)
- [done] เพิ่ม output แยกเป็น CSV (`matched_compare.csv`, `value_mismatch.csv`, `missing_in_manual.csv`, `extra_in_manual.csv`) สำหรับ review ทีละรายการ
- [done] เพิ่ม sheet filter อัตโนมัติ: ตัดชีทสรุป/non-driver และเหลือเฉพาะชีทที่ map กับคนขับในระบบ
- [next] ปรับ extraction `manual_net` ให้เชื่อถือได้ (ปัจจุบันหลายชีทยังได้ 0 จากสูตร/โครงชีท) หรือกำหนดให้เทียบเฉพาะ `trip_fee/petty/fuel_rate` เป็นหลักก่อน

## ⭐ Quick Status (2026-05-02 | One Platform — หน้า pitch สำหรับ Pages)

- [done] **`reports/one-platform-status/`** บน **`yk-logistics/transport-rate-calculator`** — `index.html` + **`public-stats.json`** (สถิติรวมจริงจาก `app.db`) + `build_public_stats.py` + README — push แล้ว (ลิงก์ด้านล่าง CONTEXT_LOG)
- [next] หลัง import/DB เปลี่ยนมาก: รัน `python ProjectYK_System\docs-public\one-platform-status\build_public_stats.py` → copy โฟลเดอร์ไป `transport-rate-calculator-repo` → push อีกครั้ง

## ⭐ Quick Status (2026-05-01 | Oatside — GitHub Org `yk-logistics`)

- [done] **`trips.html` + ตารางรายเที่ยวต่อทะเบียน**: คอลัมน์ **ค่าขนส่ง / เสียเวลา+50% / เสียเวลา+100% / ตีเปล่า+50%**; No-work recovery รองรับข้ามคืน (`first_no_work_trip_by_plate_recovery_day` + แถวสังเคราะห์ `plate_dest_day_rows`) — `Oatside/build_oatside_reports.py` (Session #100)
- [done] **Oatside hotfix ค่าเสียเวลาให้ยึดค่าขนส่งจริง**: หน้า `reports/oatside-pg-2026/trips.html` และ `reports/oatside-pg-2026/plates/*.html` เพิ่ม script re-calc ค่า `เสียเวลา+50%`/`เสียเวลา+100%` จาก `ค่าขนส่ง(฿)` ต่อแถว (50%/100%) แบบ 2dp
- [done] **อธิบายคอลัมน์เงิน + dedupe `origin24h`** (สูงสุด 1 ครั้งต่อทะเบียน×วัน Dest_In) + **หัวตาราง sticky** ในกรอบเลื่อน — Session #101
- [done] **แบ่งกลุ่มตามวันในตารางเที่ยว** — พื้นหลังสลับโทน `day-band-0`/`day-band-1` (matched ยึดวัน **Origin_In**; UM-D ใช้เวลา leg) + **เรียง matched ตาม Origin_In** — Session #102
- [done] **`manual_extra_trips`** (เช่น 72-1217 22/4/2026 P&G→Oatside +7,500 ไม่มีใน GPS) — บวกฐาน/สรุปลูกค้า + ชีต `Manual_Extra_Trips` — Session #103
- [done] **`manual_return_trips`** (ค่าขนส่งขากลับ flat +7,500 — ไม่เพิ่ม matched; คอลัมน์ **ขากลับ(฿)** + ชีต `Manual_Return_Trips`) — Session #104
- [done] **`trips.html` กรอง/ค้นหาทะเบียน** + **`index.html` พับหัวข้อสรุป** (`section-fold`, Audit/รายทะเบียน style เดียวกัน) — `apply_oatside_ui_trips_filter_index_fold.py` — Session #105
- [done] **Excel ลูกค้า**: ไฟล์แยกต่อตารางใน **`exports/*.xlsx`** + จัดรูปหัวตาราง/สีแถว + ลิงก์จาก **`index.html`** — `patch_oatside_excel_exports.py` — Session #106
- [done] **Excel `Trip_Detail`**: เติมคอลัมน์ราคา (`Trip_rate_baht`, `Downtime_50_baht`, `Downtime_100_baht`, พร้อม `Nw_outbound50_baht`/`Return_manual_baht`) ให้ตรง logic หน้าเที่ยวทั้งหมด — Session #113
- [done] **ไฟล์ราคาแยกทั้งชุด**: `exports/15_Trips_Pricing_All.xlsx` (วันที่, ทะเบียน, ค่าขนส่ง, ค่าเสียเวลา 0/1 เที่ยว, ค่าตีเปล่า, ค่างานขากลับ) — Session #114
- [done] **Oatside pricing run-date + fuel-linked**: `Oatside/build_oatside_reports.py` คิดเรทตาม `trip_date` โดยรองรับ `diesel_price_history` ใน `oatside_config.json`, ล็อก Apr base 7,500/8,000 (ฐานน้ำมัน 50.00-50.99 + floor 6,500), เพิ่ม May base 6,500 (ฐานน้ำมัน 31.00-31.99 + step 1.5%/บาท), และงานขากลับรองรับ `percent_of_trip_rate=50`
- [done] **Oatside diesel fallback carry-forward**: ถ้าวันวิ่งไม่มีราคาน้ำมัน เปลี่ยนเป็นดึงราคาล่าสุดย้อนหลัง (`latest <= trip_date`) ก่อน; ถ้าไม่มีข้อมูลก่อนหน้าเลยค่อยใช้ base rate พร้อม warning traceable ระบุวัน/ราคา source และพิมพ์สรุปจำนวน `exact/carry_forward/base_fallback` ตอนจบ build
- [done] **Oatside diesel history applied**: เติม `diesel_price_history` จาก user-provided historical table (Bangchak ไฮดีเซล S ปี 2569) จำนวน 19 anchor dates แล้ว rerun รายงานได้ `exact=22, carry_forward=83, base_fallback=0`
- [done] **Oatside diesel typo fix Apr17-20**: ผู้ใช้แจ้ง typo `429 -> 42.90` ในช่วง `2026-04-17..2026-04-20` แก้ค่าใน `diesel_price_history` แล้ว rerun ได้ `exact=37, carry_forward=68, base_fallback=0`
- [done] **ตัดเดือน พ.ค. ออกจากรายงาน Oatside**: เพิ่ม config filter `report_end_date=2026-04-30` + โค้ดกรองช่วงรายงานใน `build_oatside_reports.py` (กรองทั้ง trips/unmatched) แล้ว rerun ได้ `Trips 103` (`105 -> 103`) และ deploy publish สำเร็จ (`b944925`)
- [done] **UX ลูกค้า**: hero ชี้ `trips.html` + Excel ขวาหัวแต่ละ `<details>` + ตัดบล็อกคำอธิบายสี — `patch_oatside_hero_xlsx_inline.py` — Session #107
- [done] **`trips.html` + หน้า plate**: แถบ **แสดง/ซ่อนคอลัมน์** (checkbox + `localStorage`) สำหรับจอแคบ — `build_oatside_reports.py` + `apply_oatside_col_toggle.py` — Session #111
- [done] **HTML Oatside — หลายป้าย/เซลล์ + ตีเปล่า (No-work recovery)**: รวม `nw_rows` ในคอลัมน์ส่วนเพิ่มตาราง (2); หน้า plate รองรับหลาย fifty ต่อวัน — `patch_oatside_multi_badge_nw.py`
- [done] **HTML Oatside — ป้าย surcharge**: เคสข้ามคืนเต็มเรทแสดง **+100%**; แยก **ตีเปล่า** vs **ค่าเสียเวลา** (`fifty_kind` + `html_fifty_surcharge_badge`) — `build_oatside_reports.py` + tools `apply_oatside_fifty_patch.py` / `patch_oatside_audit_sub.py`
- [done] **`OATSIDE_BACKEND_SCHEMA.md`** — พิมพ์เขียว schema + prompt ตัวอย่างสำหรับโยน **Claude บนเว็บ (Artifacts)** ออกแบบ Dashboard mock (`TransportRateCalculator/docs/OATSIDE_BACKEND_SCHEMA.md`)
- [done] **`customer_idle_windows`** (default 71-8967 ฝากโรงงาน) + คอลัมน์ **`Trip_Detail`** แยก dest wait ฝั่งลูกค้า + flag **`use_origin_24h_fifty`** (rolling 24h จาก `Origin_In` สำหรับ +50%) — `build_oatside_reports.py` + `OATSIDE_TRIP_PAIRING_MERGE_HANDOFF.md`
- [done] **default `use_origin_24h_fifty`: true** + **`customer_no_work` / recovery outbound 50%** (บรรทัด D + ชีต `NoWork_Outbound_50pct`) + **`Phantom_Trip_Candidates`** + **`Hints_DoubleOrigin`** + คอลัมน์ **`Nw_outbound50_baht`** — merge `oatside_config.json` แล้ว (Session #93)
- [done] นโยบายวัน recovery + fifty: โอยืนยัน **เก็บคู่** (บวกทั้ง fifty ดาวน์ไทม์กับ No-work outbound 50% ได้) — แถว `Policy_recovery_plus_fifty` ในชีต Info ของรายงาน Excel
- [next] โอเทียบยอดกับ Excel ชุดเดิมหลัง default origin24h + บรรทัด D
- [done] เติม `diesel_price_history` ใน `Oatside/oatside_config.json` จากข้อมูลย้อนหลังไฮดีเซลที่ยืนยันแล้ว และ rerun `python Oatside/build_oatside_reports.py` เพื่อล็อกยอดผันแปรจริง
- [done] หลังเติมน้ำมันย้อนหลังรอบแรก ตรวจแล้ว output build มี `carry_forward > 0` และ `base_fallback=0` (`exact=22, carry_forward=83, base_fallback=0`)
- [done] **จำนวนเที่ยวต่อวัน (ลูกค้า)**: ชีต Excel **`Customer_Trips_Per_Day`** + ตารางบน **`index.html`** (matched ตามวัน `Dest_In` + จำนวนรถ) — `build_oatside_reports.py`
- [done] **`match_plate` แบบปลายทางก่อน** (ต้นทางล่าสุดก่อน `Dest_In`) — ลด UM ผิดพลาด / ลดชน `demote_chronology_violations`; build ล่าสุด **105 / 15** + เอกสาร `OATSIDE_TRIP_PAIRING_MERGE_HANDOFF.md` §4
- [done] **ปิดรวบ Origin ทั้งก้อน**: `enable_origin_chain_merge` default **false** + เอกสาร `OATSIDE_ORIGIN_CHAIN_MERGE_FIX.md` + build ชุด GPS **02.05.2026** (ตัวอย่าง `ProjectYK_System/tools/run_oatside_may02_build.py`)
- [done] ย้าย repo `transport-rate-calculator` ไป org **`yk-logistics`** — รายงาน Oatside บน Pages (path เป้าหมายหลัง push): `https://yk-logistics.github.io/transport-rate-calculator/reports/oatside-pg-2026/index.html`
- [next] โอรัน **`deploy_oatside_report_one_click.bat`** จากราก Project YK (ต้องมี clone + push ได้) — จึงจะย้ายรายงานไป path ใหม่และให้ลิงก์เก่า `…/oatside-apr2026/…` เป็น 404
- [next] หากแก้ที่ source generator รอบถัดไป ให้ย้าย logic re-calc นี้กลับเข้า `build_oatside_reports.py` โดยตรง เพื่อให้ไฟล์ที่ build ออกมาถูกต้องตั้งแต่ต้นทาง (ไม่พึ่ง hotfix JS)
- [next] บนเครื่องที่รัน deploy: ในโฟลเดอร์ clone (`transport-rate-calculator-repo` หรือชื่อที่ใช้จริง) รัน `git remote -v` ให้ชี้ `https://github.com/yk-logistics/transport-rate-calculator.git` (หรือ SSH แบบ `git@github.com:yk-logistics/transport-rate-calculator.git`) และยืนยันว่า push ผ่าน
- [done] Billing Oatside: **`charge_min_trip_shortfall` default false** — ไม่เก็บเงินค่าชดเชยเที่ยวขาด (min trips) ในรายงานลูกค้าเมื่อใช้ชาร์จ 50% วันละ 1 เที่ยว; ตั้ง **true** ใน `Oatside/oatside_config.json` ถ้าต้องการโหมดเก็บทั้งค่าชดเชย + 50%

## ⭐ Quick Status (2026-04-29 | Petty เม.ย. 2569 rev.1)

- [done] Re-import ชีท **`APR 26`** จาก `data/Salary/PettyCash/2026-04/petty_cash_all_sites_2026-04 rev.1.xlsx` → `source=book2_2026`, `pay_cycle_tag=2026-04` (หลังลบของเก่าเฉพาะรอบนี้ — ไม่ wipe หลายเดือน)
- [done] **MAR 26 เป็นหลักรอบมี.ค.** — ลบซ้ำ `book2_2026` + `import_petty_mar26` (`2026-03`) → import `MAR 26` จาก `rev.1.xlsx` → **740** แถว `book2_2026`
- [next] ลด unlinked หักสดย่อยรอบ `2026-04` / `2026-03` (alias / ผูกคนขับ) แล้ว recompute payroll ที่เกี่ยวข้อง

## ⭐ Quick Status (2026-04-27 | BIGC payroll เม.ย.)

- [done] Import BIGC งาน **มี.ค. 2569** (แท็กระบบ `2026-03`): `daily_bigc_2026-04.xlsx` Sheet1 + `fuel_rate_daily_bigc_2026-04.xlsx` + `--tag 2026-03` — verification รวมเรท ~0.44 บาท
- [done] Import สดย่อยชีท `MAR 26` จาก `data/Salary/PettyCash/2026-04/petty_cash_all_sites_2026-04.xlsx` ด้วย source `import_petty_mar26` + safe driver-link
- [done] เพิ่ม Alias Map กลาง + unlinked guard (payroll banner + petty filter + finalize gate)
- [done] แก้ payroll cross-site mix (aggregate + drill-down filter ตาม site_code ของรอบ)
- [done] Surgical reset BIGC `2026-03` แบบเฉพาะจุด (backup -> wipe source-targeted -> reimport -> recompute -> preflight)
- [done] เพิ่ม income-tax withholding แบบขั้นบันไดใน payroll engine (annualized progressive -> monthly deduction)
- [done] เปลี่ยน default tax mode เป็น catch-up + แยกช่อง `income_tax_withholding` ใน payroll/UI
- [done] ตั้งเพดานหักภาษีรายเดือน default 15% (`tax_monthly_cap_rate`)
- [done] เพิ่ม alias `AYU: สมัย -> สมัย อยุธยา` + dedup สดย่อย legacy 485 แถว + reassign site=AYU 565 แถว
- [done] **PDF bundle**: ปุ่มส่งออก `/payroll/{id}/export-pdfs` → `data/Salary/{SITE}/{cycle}/Driver/` (สรุปรวม / โอนเงินบัญชี / ชุดครบ / สลิปรายคนใน `รายคน/`) — `fpdf2` + Tahoma — BIGC โฟลเดอร์ตามเดือนจ่าย + เติมเลขบัญชีจาก seed + สลิปแนวนอนหนึ่งหน้า (เมษายน 2026)
- [done] ปรับ `ProjectYK_System/tools/import_petty_cash.py`: pre-assign site จาก suffix `อยุธยา/BIG C/แหลม` ตอน insert — ผ่าน `site_from_requester()` ใน `alias_map.py`
- [next] UI ใหญ่ (cross-page): date format ไทย / multi-select filter / pagination jump-to-page
- [next] เคลียร์ชื่อซ้ำ `สมัย` (BIG C vs อยุธยา) โดยเพิ่ม master AYU หรือกำหนด mapping manual เฉพาะเคส
- [next] เทียบสลิป manual BIGC รอบ `2026-03` แล้ว finalize
- [next] master `fuel_rate.xlsx` (3) + ตรวจทาน `data/Billing/BigC/` (4)

## ⭐ Quick Status (2026-04-28 | Transport Rate Calculator UX)

- [done] เพิ่มโหมดใหม่ `บาท/ช่วง` ใน `ProjectYK_System/TransportRateCalculator/transport_rate_calculator.html` (นอกเหนือจากโหมดเปอร์เซ็นต์เดิม)
- [done] ปรับสูตร/ตารางตัวอย่าง/ผลลัพธ์/Export Excel ให้รองรับทั้ง `%` และ `บาท/ช่วง`
- [done] ทดลองปรับ Step 1 เป็น "ย้อนหลัง+ไฮดีเซล S" แล้ว
- [done] rollback กลับ Step 1 แบบเดิม เพราะ historical page บล็อก iframe (`refused to connect`)
- [done] เพิ่ม Step 1 แบบใหม่: ดึงราคาน้ำมันย้อนหลังรายวันจากเว็บ + คลุมช่วงเพื่อหาเฉลี่ยแล้วใส่ราคาน้ำมันอัตโนมัติ
- [done] ล็อก baseline สูตรเสนอราคาแบบทำในแชทสำหรับงาน Direct-to-store: `((700000/8)+13500)/365 + น้ำมัน + maintenance 1.5 + ค่าเที่ยว + back office 12%` และคุม drop charge 400-600
- [done] ปรับ baseline Direct-to-store ให้แยก consumption ตามประเภทรถ: 6W `5.5 กม./ลิตร`, 10W `4.5 กม./ลิตร` และเพิ่มคอลัมน์ `%น้ำมันต่อค่าขนส่ง`
- [done] เพิ่ม fuel escalation model ในไฟล์เสนอราคา: ใส่ `% ปรับต่อ 1 บาท` และน้ำมันเป้าหมายได้ พร้อมคอลัมน์ break-even `%/บาท` รายรูท
- [done] อัปเดตดีล Direct-to-store เป็นเงื่อนไขลูกค้า `1.5% ต่อ 1 บาท` (`P21=0.015`) และ reprice ให้ยังถือ target margin ~10% ที่ fuel target 50
- [done] ปรับดีล Direct-to-store เพิ่ม: consumption 6W = 5.0, trip fee ladder ตามระยะ (0-200=500/600 แล้ว +100 ต่อทุก 100 กม.), และโซนเน้นงาน (สมุทรปราการ/ฉะเชิงเทรา/ชลบุรี) ใช้ target margin 5%
- [next] push ขึ้น remote เพื่ออัปเดต GitHub Pages และให้ผู้ใช้ทดสอบหน้าเว็บจริง
- [next] ถ้าเจอจุดที่ดึงย้อนหลังไม่สำเร็จจาก browser (CORS/proxy blocked) ให้เพิ่ม backend fetch endpoint ภายในโปรเจกต์เพื่อลดความเสี่ยงข้อมูลไม่ขึ้น
- [done] เพิ่ม fallback ในหน้าเดียวกัน: วางข้อมูลที่คัดลอกจากเว็บแล้ว parse เป็นตารางย้อนหลังได้ (ไม่ต้องพึ่ง fetch สำเร็จ)
- [done] parser รองรับ tab-separated จากเว็บตรงๆ (วันที่ + ราคาหลายคอลัมน์) และ map คอลัมน์ตามชนิดน้ำมันที่เลือก
- [done] เติมวันที่ที่หายใน series รายวันอัตโนมัติ (carry-forward ราคาวันก่อน) + แสดง badge `เติมวันหาย`
- [done] เพิ่มเลือกช่วงวันที่ `ตั้งแต่-ถึง` แล้ว select แถวเพื่อเฉลี่ยอัตโนมัติ
- [done] เปลี่ยน workflow วันที่/ปีใน panel ย้อนหลังเป็นค.ศ.ทั้งหมด (input/filter/display)
- [done] เพิ่มปุ่ม `Export CSV ตารางย้อนหลัง` บน historical panel และส่งออกไฟล์ `UTF-8 BOM` พร้อมคอลัมน์ trace (`date/fuel_type/price_baht_per_liter/imputed/selected`) และชื่อไฟล์มีช่วงวันที่ข้อมูล
- [next] ทำ template prompt สำหรับลูกค้า ad-hoc รายใหม่ (ไฟล์ไม่มาตรฐาน) ให้ใส่ข้อมูลขั้นต่ำ 8 จุดแล้วคำนวณได้ทันที
- [next] เพิ่มตาราง stress test น้ำมันเพื่อหา break-even/base rate ขั้นต่ำแบบเร็ว
- [next] ทดสอบ UAT หน้าเครื่องคิดเรท: ดึงย้อนหลัง -> คลุมช่วง -> Export CSV แล้วเปิดใน Excel ว่าฟอนต์ไทยและช่วงวันที่ในชื่อไฟล์ตรงข้อมูลจริง

## ⭐ Quick Status (2026-04-28 | YK shared-yard leasing risk)

- [next] ทำ decision sheet พื้นที่เช่า 1 หน้า: เทียบ 3 ทางเลือก (ลานพักรถ/คิวงาน, cross-dock เบา, ผู้เช่า workshop เบา) โดยยึดรายได้ขั้นต่ำ >= 34,000/เดือน
- [next] เพิ่ม constraint บังคับใน decision sheet: ทางเข้า-ออกรถใหญ่ติดข้อพิพาททางกฎหมาย (คดีถนนเข้าออก) จึงต้องคัดโมเดลที่พึ่งพารถหนักน้อยลงชั่วคราว
- [next] เก็บตัวเลข peak utilization ลานจอด วาย.เค (รถตัวเอง + รถลูกค้า) แยกช่วงเวลา เพื่อกำหนดเพดานรถของผู้เช่ารายใหม่
- [next] ทำ traffic log 14 วัน (จำนวนเที่ยวเข้า/ออก แยกขนาดรถและช่วงเวลา) เป็นฐานกำหนดเงื่อนไขสัญญาเช่า
- [next] ร่าง checklist สัญญาเช่าแบบกันความเสี่ยงข้อมูลตกหล่นหน้างาน: zoning, น้ำไฟ, ความสะอาด, ค่าปรับน้ำมัน/ของเสีย, SLA การเคลียร์พื้นที่

## ⭐ Quick Status (2026-04-25 | KYT Weekly playbook)

- [cancelled] ผู้ใช้ขอถอด KYT ออกจากโปรเจกต์ และกลับไปใช้ Cursor chat workflow ชั่วคราว
- [next] หากผู้ใช้ต้องการกลับมาทำ KYT ในระบบอีกครั้ง ค่อย rebuild เป็นโมดูลใหม่ที่ผ่าน UAT ก่อนเปิดใช้งานจริง

## ⭐ Quick Status (session #25 | Phase 4 Wave 1 DONE)

**Session #25 (2026-04-08 late): Phase 4 Wave 1 — Driver PWA (Auth + Vehicle Check + Alcohol Test)**
- **Schema v14**: `Employee.pin_hash` + `DriverSession` + `DriverSubmission` (kind: vehicle_check/alcohol_test/job_photo/fuel_receipt/signature/other)
- **`services/driver_auth.py`**: stdlib scrypt PIN hash, in-memory rate limit (5/10min), phone normalize, cookie session 30d rolling, photo save to `uploads/driver/<emp>/<date>/<kind>/`
- **Mobile-first PWA (6 หน้า)**: `/driver/login` · `/driver` (home + daily status tiles) · `/driver/today` · `/driver/check` (15-item checklist + photos + GPS) · `/driver/alcohol` (reading + photo + GPS + auto-flag if > 0) · `/driver/history`
- **Client-side compression**: JPEG 1280px@75% → ประหยัดแบนด์วิดท์ 4-10x (สำคัญสำหรับ 4G ในสายงาน)
- **Admin**: `/admin/drivers/pins` (set/clear + revoke sessions), `/admin/submissions` (filter driver/kind/review/date + review workflow + photo preview)
- **E2E test PASS**: login → submit check+alcohol → admin review → logout → cleanup
- **หมายเหตุ**: PWA = website ที่ทำงานเหมือนแอพ, เปิดบน browser มือถือได้เลย ไม่ต้องโหลดจาก Play Store

## ⭐ Quick Status (session #17–23 | Phase 3 DONE)

**Session #23 (2026-04-08): Phase 3 — CFO Dashboard**
- **Schema v13**: `Loan` + `LoanPayment` (6 ประเภท: term / hire_purchase / revolving / informal / factoring / other)
- **`services/finance.py`** ใหม่ (ทุกสูตรการเงินรวมที่เดียว):
  - `amortization_schedule` (ลดต้นลดดอก / งวดคงที่ / ดอกเบี้ยอย่างเดียว)
  - `loan_summary` (ยอดรวม / ภาระ/เดือน / ประมาณดอก 12 เดือนหน้า)
  - `monthly_pnl` — รายรับ vs ต้นทุน (petty กรองซ้ำกับ fuel/maint, toggle "รวม other" ได้)
  - `cost_per_vehicle` — รายรับ/น้ำมัน/ซ่อม/gross margin ต่อคัน
  - `cash_flow_projection` — 30-180 วันข้างหน้า (AR M+1, หนี้, payroll, avg daily)
  - `break_even_and_runway` — contribution margin + break-even trips/เดือน
- **หน้าใหม่ `/finance/*`** (6 endpoint):
  - Dashboard หลัก · หนี้ CRUD + ตารางผ่อน auto · P&L รายปี · ต้นทุนต่อคัน · Cash Flow
  - รองรับฟอร์มกรอกหนี้เอง → ผู้ใช้ทยอยเพิ่มได้เมื่อได้ข้อมูลจากพ่อ (ไม่บังคับ)
- **สมจริง**: Feb 2026 = net profit +160k (7.4% margin) · avg rev/trip 3,798฿ · break-even 80 trips/เดือน
- **`.gitignore`** ใหม่: กัน *.db, `data/`, xlsx/pdf, secrets, nested .git

## ⭐ Quick Status (session #17–22 | Phase 2 DONE)

**ทำแล้ว:** Petty Cash CRUD, Daily import (script + **v12 provenance** `DailyJob.source`, default history from **2018-01-01**, safe `--wipe-prior`), Fuel UI + Caltex import,
Promote raw→master (44 Employee + 169 Vehicle), **Payroll MVP v1** (สูตร 3 ไซต์ครบ,
สร้าง PayRun Feb 2026 ได้), **Payroll v1.1**: BIGC fuel_rate 16฿, AYU toll deduction,
drilldown `/payroll/{id}/employee/{id}` print-friendly,
**Billing export (P0-3)** `/billing` + `/billing/export.csv` — สรุปต่อลูกค้า + ดาวน์โหลด CSV,
**Dependency pin**: `starlette<0.40` + `fastapi<0.115` (starlette 1.0 แตก Jinja2).

**Data ใน DB ตอนนี้**:
- DailyJob **1,552 rows** (Jan–Mar 2026) — 93% linked driver / 100% linked vehicle
- PettyCashTxn **50,753 rows** (2019-12 → 2026-06) — 20% linked driver (ที่เหลือ = พ่อ/office/คนขับเก่า ต้อง promote)
- FuelTxn **777** · DailyJobFee **1,215** · RateCard (auto-learned) **1,167 unique patterns**
- Backfill script `ProjectYK_System/tools/backfill_links.py` ใช้เติม FK หลัง wipe+import ได้ทุกเมื่อ
**Ops fixes**: default port 8010 + `SO_EXCLUSIVEADDRUSE` listen-test (กัน 10048),
browser auto-open, Employee.role, additive schema migration.

**Session #19 (2026-04-08): BIGC Fuel Rate Option B — per-trip import**
- **`ProjectYK_System/tools/import_bigc_fuel_rate.py`** นำเข้าเรทน้ำมัน BIGC 3 เดือน (ธ.ค.2568 / ม.ค.-ก.พ.2569)
  - parse ชีท `รวมเรท` (authoritative) + ชีทคนขับ (per-trip detail)
  - upsert `DailyJob.fuel_liter` = งบ, สร้าง `FuelTxn` (source=`bigc_fuel_rate`)
  - แก้ FuelTxn ซ้ำ (import_daily vs bigc_fuel_rate) — ล้าง source ที่ override ก่อน
  - zero-out DailyJob.fuel_liter ก่อน เพื่อกัน stale budget จากรอบเก่า
- **Models**: `PayRunAdjust` เก็บ adjust_liter ต่อ (PayRun, Employee) — รอดจาก recompute
- **Calc fix**: rebate ติดลบได้ (admin ต้องหักคนขับที่ใช้น้ำมันเกิน)
- **Audit UI**: แสดง งบ / ใช้จริง / residual / rebate + admin adjust ในหน้า drilldown
- **Verification**: ABS DIFF ทุกเดือน < 1 บาท (floating-point rounding เท่านั้น)
- **Unmatched drivers**: "อาท" ยังไม่มีใน Employee master (ต้อง promote)

**Session #20 (2026-04-08): Maintenance Module — Wave 1 (MaintRecord + Vendor + Part + Stock)**
- **Schema v8** เพิ่มครบ: `Vendor` / `Part` / `StockTxn` / `MaintRecord` / `MaintPart` / `Tire` / `TireEvent` / `PmPlan`
  (Wave 2–3 จะต่อ UI ยาง & PM ที่หลัง — ตารางพร้อมใช้แล้ว)
- **ENUMs ล็อก:** MAINT_KINDS / MAINT_STATUS / MAINT_PAID_BY / PART_CATEGORIES / PART_UNITS /
  VENDOR_KINDS / TIRE_STATUS / TIRE_EVENT_TYPES / PM_KINDS / TIRE_POSITIONS_BY_KIND
- **UI Wave 1 เสร็จ:**
  - `/maint` — Dashboard (สถิติเดือนนี้, cost by vehicle, recent 10)
  - `/maint/records` — list + filter (วันที่/รถ/ประเภท/สถานะ) + summary
  - `/maint/records/new` + `/maint/records/{id}` — CRUD บันทึกซ่อม พร้อม line-items อะไหล่
  - `/maint/vendors` — master ร้าน/อู่
  - `/maint/parts` — master อะไหล่ + live stock + low-stock alert
  - `/maint/stock` — รับเข้า/เบิกออก/ปรับยอด + 100 รายการล่าสุด
- **Auto-logic:**
  - เพิ่ม MaintPart ที่ link กับ Part master → สร้าง `StockTxn(direction='out')` อัตโนมัติ
  - รับ stock-in → อัปเดต `Part.default_price` อัตโนมัติ
  - parts_cost/total_cost บน MaintRecord re-sum อัตโนมัติเมื่อเพิ่ม/ลบ line
  - auto-code: V0001 / P0001 / M000001
- **Smoke test:** 8 routes GET 200, POST create+edit+line-items+delete ครบ
- **Wave 2 (ยาง):** UI lifecycle ดอกยาง ตำแหน่ง (FL/FR/RLO/… ตามประเภทรถ)
- **Wave 3 (PM/RM):** หน้าแผน PM + auto-แจ้งเตือนเมื่อถึงกำหนด (km/วัน)

**Session #21 (2026-04-08): Rate Book + Auto-learn — Wave 1**
- **Schema v9**: `RateCard` table (kind × site × customer × vehicle_kind × trip_type × origin × destination × pickup_location)
- **Auto-learn**: ทุกครั้งที่ save DailyJob → auto-record 3 kinds (fuel/revenue/trip_fee) ผ่าน `rate_record_from_daily()`
- **Pattern matching**: scoring +10 exact / +1 wildcard `*` · priority ทiebreak · manual > auto
- **UI**: `/rates` list + filter + `/rates/new` + `/rates/{id}` edit + delete
- **API**: `/api/rates/suggest` — HTMX-ready JSON endpoint (Wave 2 จะ hook เข้า DailyJob form)
- **Backfill**: `/rates/backfill` one-click → scan DailyJob ทั้งหมด (1,550 rows → **1,167 unique patterns learned**)
  - trip_fee_driver: 492 rules
  - revenue_customer: 393 rules
  - fuel_budget_liter: 283 rules (BIGC งบลิตรต่อสาขา)
- **Examples of what was learned:**
  - AYU `บางพลี นีเวีย → Big-C บางปะอิน` 6W: ค่าขนส่ง 3,046฿ / ค่าเที่ยว 1,827.6฿ (x18 uses)
  - LCB `CDS → C1C2` loading=`DAIKIN FAC อมตะ` 6W Export: ค่าขนส่ง 4,200฿ / ค่าเที่ยว 2,520฿ (x2)
  - BIGC → Samutprakarn: งบน้ำมัน 60L (x8 uses)
- **Promote auto→manual**: admin กดเช็คบ็อกซ์ใน edit form → source=manual, priority+=1 (กัน auto update ทับ)

**ลำดับถัดไปที่แนะนำ:**
1. **Rate Book Wave 2** — hook HTMX เข้า DailyJob form (พิมพ์ origin/dest/vehicle → auto-fill ค่าขนส่ง/ค่าเที่ยว/งบน้ำมัน)
2. **Maintenance Wave 2 (Tire)** — UI ยาง ตำแหน่ง สลับ/หล่อดอก
3. **Maintenance Wave 3 (PM/RM)** — แผน PM + แจ้งเตือนถึงกำหนด
4. **Promote "อาท"** ผ่าน /admin/promote แล้ว re-import BIGC fuel rate
5. **Data gap filling** — AYU DailyJob Feb 2026 / LCB trip_fee
6. **Excel diff tool** — เทียบ PayRun กับ `บันทึกประจำเดือน YK.xls` / `หัวลาก.xlsm`
7. **Dispatch UI** — หน้าคีย์งานใหม่ (ต้นน้ำ) + notify ไลน์
8. **Billing** — ออกวางบิลจาก DailyJob
9. **UI ที่ยังขาด:** `/leaves`, `/accidents`, `/deposits`, `/pay-cycles`

## Phase 0: Lock Blueprint (ทำก่อนเขียนระบบจริง)

1. จัดทำ `DATA_DICTIONARY.md` [done]
   - ฟิลด์มาตรฐานกลางทั้งหมด
   - mapping ต่อไซต์ AYU/BigC/LCB

2. จัดทำ `JOB_STATUS_FLOW.md` [done]
   - สถานะงานตั้งแต่รับงานจนปิดบัญชี
   - เงื่อนไขเปลี่ยนสถานะและผู้อนุมัติ

3. จัดทำ `CUSTOMER_BILLING_PROFILE_TEMPLATE.md` [done]
   - เงื่อนไขออกวางบิลรายลูกค้า
   - เอกสารแนบที่ต้องใช้
   - กฎ billable/non-billable

4. เติมข้อมูลจริงลูกค้า 3-5 เจ้าแรกลง profile [next]
   - สร้าง seed profile แล้วใน `CUSTOMER_BILLING_PROFILES.md`
   - งานคงเหลือ: ยืนยันกับทีม Billing หน้างาน [next]

5. ล็อก enum กลางทั้งหมด [done]
   - job_status
   - petty_cash_category
   - payroll_pay_type
   - invoice_status

6. ล็อก policy การแก้ข้อมูลหลังปิดรอบ [done]

## Phase 0.5: Ready for Build

7. ล็อก API contract v1 (request/response) [done]
8. สร้าง SQL schema v1 จาก `DATA_DICTIONARY.md` [done]
9. เตรียม migration/import script สำหรับ AYU/BigC/LCB [next]

## Phase 0.6: Build Bootstrap

10. จัดทำ `IMPORT_MAPPING_SPEC.md` สำหรับแต่ละไซต์ [done] (3 ไซต์ AYU/BIGC/LCB จากตัวอย่างจริง `ProjectYK_System/Daily.xlsx`)
11. จัดทำ `VALIDATION_RULEBOOK.md` พร้อม severity [next]
12. สร้างไฟล์ `migrations/001_init_schema.sql` จาก `SQL_SCHEMA_V1.md` [next]
13. จัดทำ `SITE_PAYROLL_RULES.md` [done]
14. จัดทำ `BIGC_BRANCH_RATE_SPEC.md` [done] — รอไฟล์ตารางสาขาจากผู้ใช้
15. จัดทำ `WORKFLOW_BY_TEAM.md` [done]

## Phase 1.0: Day-1 Skeleton

16. เลือก stack: FastAPI + SQLite + HTMX + Tailwind CDN [done]
17. สร้างโครงแอปที่ `ProjectYK_System/app/` [done]
    - `main.py` + templates + `start.bat` + README
    - CRUD ขั้นต้นของ `DailyJob` + ฟิลเตอร์ site/วันที่
    - ทดสอบ server ขึ้น + `/health` ok
18. ผู้ใช้ทดสอบ start.bat ผ่าน [done]
19. ตั้ง Cursor rule ให้ agent auto-update context [done]
    - `.cursor/rules/project-yk-context.mdc` (alwaysApply=true)

## Phase 1.1: Expand Data Model to Cover 3 Sites

20. ขยาย `DailyJob` schema [done]
    - เพิ่ม: `doc_no`, `job_ref`, `trip_type_code`, `container_no`, `container_size`, `fuel_liter`, `fuel_amount`, `fuel_station`, `fuel_rate_km_per_l`, `mile_snapshot`, `invoice_no`, `invoice_date`, `wht_53`, `leave_status`, `status_code`, `head_vehicle_id`, `tail_vehicle_id`, `plate_no_raw`, `tail_plate_raw`, `driver_id/driver_raw_name`, `customer_id/customer_name_raw`, `trip_group_id`
    - เพิ่มตาราง `daily_job_fees` (lift/yard/clean/shore/port/weighing/special/ot/pickup_return/mflow/shared_vehicle/other) — table อยู่ใน schema v2 แต่ยังไม่มี UI
21. สร้างตาราง Master Data [done]
    - `employees` — รวม pay contract ฟิลด์ไว้บนแถวเดียว (pay_mode, base_salary, care_allowance, gross_share_rate, has_guarantee, guarantee_amount, deposit_target, deposit_balance, social_security_*, custom_terms) — ยังไม่แยก history table ไว้ทำ Phase 2 เมื่อมีของจริง
    - `vehicles` (vehicle_kind: head/tail/truck, truck_type, home_site_code, status)
    - `customers` (code, name, home_site_code, billing_profile_ref)
22. สร้างตาราง payroll support [done - ตาราง/ยังไม่มี UI]
    - `leave_records`, `accident_cases` + `accident_installments`
    - `driver_deposits` (running balance เงินประกันตน)
    - `pay_cycles` (AYU 26-25, BIGC 1-end, LCB 16-15) — seed อัตโนมัติ startup
23. สร้างตาราง BIGC branch rates [done - ตารางว่าง รอ import] — ผู้ใช้ต้องส่งไฟล์สาขา+rate
24. หน้า Master Data UI + dropdowns [done]
    - /employees, /vehicles, /customers: list + new + edit + delete
    - /daily/new และ /daily/{id}/edit: dropdown ดึงจาก master + ยังคงมี raw_name fallback
    - `SchemaInfo` table track version (ปัจจุบัน v2)

### Phase 1.1.5: UI ส่วนที่ยังขาด [next]

20a. ส่วน `daily_job_fees` ในหน้า Daily form (กรอกค่าย่อย LCB) [next]
22a. UI `/leaves` (บันทึกลาคนขับ) [next]
22b. UI `/accidents` (เคส + งวดผ่อน) [next]
22c. UI `/deposits` (มุมมองประกันตน) [next]
22d. UI `/pay-cycles` (ดู/แก้รอบ) [next]
23a. ฟอร์ม import BIGC branches จาก Excel [next]

## Phase 1.2: Track A — Petty Cash Quick Win (NEW PRIORITY)

ผู้ใช้เสนอทำก่อนเพื่อให้แอดมินหยุดใช้ Excel เร็วสุด (เป้า 1 สัปดาห์):

A1. ตาราง ``PettyCashTxn`` [done] — 20+ fields ครอบ Excel เดิม 25 คอลัมน์, schema v3
A2. UI ``/petty-cash`` (list + new + edit + delete) [done] — 6 filters, 3 summary cards, lock guard
A3. Parser memo ไทย [done]
    - ใช้ใน ``ProjectYK_System/tools/import_petty_cash.py`` — category จาก column + memo keyword
    - extract plate regex, fallback driver_advance ถ้ามี deduction
A4. Import Excel สดย่อยเก่า [done]
    - พบไฟล์ 3 folder เป็น duplicate (99.1%) → import ไฟล์ mtime ล่าสุดครั้งเดียว
    - site_code="" (unassigned); ต้องรอ Employee master → A-Site-Assigner
    - **รอบแรก:** 50,753 rows 2019-2026 — ผู้ใช้รู้สึก UI กระตุก + คนลาออกเยอะแล้ว
    - **ปรับปรุง:** เพิ่ม `--from-date` (default=2026-02-01) เหลือ **1,366 rows** เร็วขึ้นชัด
    - `ProjectYK_System/tools/import_petty_cash.py --from-date YYYY-MM-DD --wipe-prior` เปลี่ยน cutoff ได้
A5. View "รอหักคนขับ" [done]
A5b. View "รอเคลียร์ใบเสร็จ/ทอน" [done] — /petty-cash/clearance + age-based highlight
A6. Deduct → Payroll lock hook [next] — จะทำตอนเริ่ม Payroll module
A7. Doc ``PETTY_CASH_SPEC.md`` [done] — §8-11 update
A8. **Schema v4** — เพิ่ม pending_amount/pending_note/pending_cleared_at [done]
A9. **Cycle override UX** — form helper + list badge [done]
A10. **Site-Assigner** [next] — match requester_raw → Employee.full_name
     → เติม driver_id + site_code ให้ rows ที่ import (รอผู้ใช้ seed employees ก่อน)
A11. **Daily Job Suggester** [done] — `GET /api/daily-jobs/suggest`
     - score: driver_id +3, ชื่อ +2, ทะเบียน +2, ไซต์ +1, ใกล้วัน +0.5
     - ใน petty_form ปุ่ม "🔍 แนะนำ Job" ดึงรายการ Job ที่น่าจะเกี่ยวคลิกกรอก ID ได้
     - ใช้ได้เต็มรูปแบบหลังจาก Track B (import Daily) เสร็จ
A12. **Pagination /petty-cash** [done] — 100 rows/page, COUNT/SUM ทำใน SQL
     - ป้องกัน lag เวลา import หลายหมื่นแถว
     - รักษา filter state ข้ามหน้า

## Phase 1.3: Track B — Ingestion: Import Daily Excel

B1. ตารางเสริม `FuelTxn` [done] — schema v5
    - vehicle_id FK, driver_id FK nullable, txn_date, liter, amount, price_per_liter,
      rate_km_per_l, mile_snapshot, station, fill_type, daily_job_id FK
    - เพิ่ม `pickup_location`, `store_code`, `truck_type_raw` ใน DailyJob ด้วย
B2. UI `/fuel` (list + new + edit + delete + filter + pagination) [done]
    - Filter: site, date-range, plate, driver, station
    - Summary: total liter, total amount, avg ฿/L
    - เพิ่มลิงก์ใน nav "น้ำมัน"
    - Daily form ยังคง field fuel ไว้ก่อน (ไม่ย้ายออก ตามสเปคเดิมที่ว่าเปลี่ยนตอน form redesign)
B3. สคริปต์ `ProjectYK_System/tools/import_daily.py` — 3-in-1 (AYU/BIGC/LCB) [done]
    - site adapter pattern — `import_ayu`, `import_bigc`, `import_lcb`
    - สร้าง DailyJob + DailyJobFee (LCB extras) + FuelTxn พร้อมกัน
    - คง placeholder/idle/leave rows ไว้ (status_code / leave_status)
    - `--wipe-prior`, `--from-date`, `--site`
B4-B5. รวมอยู่ใน B3
B6. ทดสอบด้วยข้อมูล Feb-Mar 2026 — cross-check [done]
    - AYU 592 rows (406 real, 173 idle, 13 leave) — ค่าขนส่งรวม 1,081,270 ✅ ตรงกับ Excel R1
    - BIGC 373 rows (219 real, 145 placeholder, 9 leave) — 894,499 ≈ R1 896,813
    - LCB 585 rows (402 real, 154 idle, 37 leave, extras: 1,215 fees) — 1,732,784
    - Fuel รวม 533 fills, เฉลี่ย ฿30.0/L ทั้ง 3 ไซต์
B7 / A10. Workflow "promote raw → master" [done] — session #16
    - `app/services/promote.py` ใช้ union-find clustering + site-majority guard
    - `/admin/promote` UI 2 tabs ติ๊กทำงานได้
    - รันครั้งแรก: 44 Employee + 69 Vehicle, backfilled 3,033 rows (DailyJob driver 1443, vehicle 1550, Fuel ทั้งหมด 788×2, PettyCash 802)
    - เหลือ 107 DailyJob (ว่าง/placeholder) + 564 PettyCash (พ่อ/แอดมิน) รอ user ตัดสินใจเอง
B8. Import Caltex fuel statement (LCB authoritative) [done] — session #15
    - `ProjectYK_System/tools/import_caltex_fuel.py` รับ 4 sheets, match DailyJob ±1 day
    - Imported 553 rows (36,261 L / ฿1.09M), matched 309 (55.9%)
    - Unmatched 244 ส่วนใหญ่อยู่นอกช่วง Daily หรือเป็นรถพ่อบ้าน (บษ2681)
    - Audit: `data/Fuel/caltex_import_unmatched.csv` + `data/Fuel/caltex_import_shifted.csv`
    - Wiped Daily-sourced LCB FuelTxn (298 rows) ออกแล้ว เพราะ Caltex authoritative กว่า
B9. UI `/fuel` source badge + filter [done] — session #15
    - Filter: source (caltex/import_daily/manual), linked (yes/no)
    - Badge สี: Caltex=emerald, Daily=sky, manual=slate
    - Highlight "ยังไม่เชื่อม" สำหรับ daily_job_id=null
B10. Manual link/review UI สำหรับ unmatched Caltex rows [next]
    - แสดงรายการที่ daily_job_id=null พร้อมปุ่ม "ค้น Daily Job ที่ใกล้เคียง"
    - ใช้ `/api/daily-jobs/suggest` เดิม + option "mark as non-driver" (พ่อบ้าน ฯลฯ)

## Phase 1.4: Dispatch (ต้นน้ำตาม vision)

29. หน้า Dispatch สร้าง Job (site, customer, origin, destination, pickup_time) [next]
30. จับคู่ vehicle + driver (แสดง rev/hours สะสม balance งาน) [next]
31. ปุ่ม "แจ้งคนขับ" — copy ข้อความไป Line group (Line OA ทีหลัง) [next]
32. Dispatch → Daily auto-fill (ให้บัญชีหยอดเลขเพิ่ม) [next]

## Phase 1.5: Billing + Payroll + Petty Cash (รวมร่าง)

33. Billing: เลือก cycle + customer → preview → export (รวมข้ามไซต์ได้) [next]
34. Petty Cash module: บันทึกรายรับ/รายจ่าย + หักคนขับ (link daily_job) [done]
35. **Payroll MVP** [done] — session #17
    - `services/payroll.py`: compute_period, compute_pay_cycle_tag, calc_one_employee
    - รองรับ 5 pay_mode: bigc_monthly, lcb_monthly, lcb_mao, ayu_trip (+ guarantee), ayu_mao
    - PayRun + PayRunItem tables (schema v6)
    - UI /payroll: list, new, detail, recompute, finalize, delete
    - Finalize lock: update PettyCashTxn.deduction_status='deducted' + status='locked'
36. **Payroll v1.1** [next] — สูตรยังไม่ครบ:
    - BIGC: `fuel_rate_income` (ลิตรคงเหลือ × 16฿) — ต้อง map DailyJob ↔ FuelTxn
    - LCB_mao: validate fuel_cost_self ตรงกับ Caltex
    - AYU_mao: รองรับ deduction ทางด่วน/Mflow จาก PettyCashTxn category=toll
    - Cross-check กับ Excel `สดย่อยวังน้อย.xlsx` รอบ Feb 2026
37. Payroll audit trail (payslip PDF + diff report vs Excel) [next]
38. Non-driver Employee / office petty-cash [next] — ออฟฟิส/พ่อ/ช่าง มี role แล้วแต่ยังไม่มี UI ดูเฉพาะ role

## Phase 1.5: Production

37. Line OA integration (notify คนขับจริง) [next]
38. ย้าย SQLite → PostgreSQL [next]
39. ขึ้น PC Server + Tailscale + one-click installer [next]
40. Backup script + 3-2-1 policy [next]

## Phase 0.7: Petty Cash Online (Quick Win)

13. ย้ายข้อมูลสดย่อยย้อนหลังขึ้นออนไลน์ [done]
   - มีสคริปต์ `tools/build_petty_cash_online.py`
   - มีรายงาน `reports/petty-cash-online/index.html`
   - มี output `petty_cash_records.csv/json` และ `summary.json`

14. ยกระดับ parser memo ไทย (ชื่อ + รายละเอียด + จำนวน + หัก) [next]
   - เพิ่ม confidence score
   - ส่งรายการไม่มั่นใจเข้าคิวตรวจ

15. ผูกหมวด Finance เข้าต้นทุนจริงรายเที่ยว [next]
   - แยกเงินต้น/ดอกเบี้ย/ค่าธรรมเนียม
   - map กับทะเบียน + สัญญาไฟแนนซ์

## Phase 1: MVP Runtime

4. ทำ Dispatch module (ต้นน้ำ)
   - หน้าสร้างงาน
   - หน้าจัดรถ/คนขับ
   - รายได้สะสมคนขับเพื่อ balance งาน
   - ปุ่มสร้างข้อความส่งไลน์

5. ทำ Daily + Import Adapter
   - import ไฟล์เดิมรายไซต์
   - normalize + validation gate

6. ทำ Billing + Payroll รุ่นใช้งานจริง
   - ออกสรุปวางบิล
   - สรุปเงินเดือนรายไซต์
   - audit trail

## Phase 2: Finance & Maintenance

7. Petty cash เต็มรูปแบบ
   - pending deductions
   - advance/return tracking

8. Maintenance & Stock
   - PM/RM
   - tire history
   - stock movement
   - maintenance KPI

## Definition of Done (รอบแรก)

- ปิดรอบ 16-15 ได้ในระบบเดียว
- ได้ 4 output หลัก:
  - Daily_Normalized
  - Billing_Summary
  - Payroll_Summary
  - Cashflow_Summary
- มี backup อัตโนมัติรายวันและทดสอบ restore ได้

---

## 2026-05-08 Email Inbox + Excel-like Grid

- [done] เพิ่ม IMAP inbox foundation:
  - schema `InboxEmail` / `InboxSyncRun`
  - service `app/services/email_ingest.py` (sync + classify + run log)
  - UI `/email/inbox` (read-only + filter + mark reviewed/ignored + reclassify)
- [done] เพิ่ม AI guardrail:
  - rule-first + optional Gemini (`EMAIL_GEMINI_ENABLED=1`)
  - บังคับ `needs_review=True` และ `suggested_action=review_only`
- [done] เพิ่ม Daily Excel-like POC:
  - หน้า `/daily/grid` (Tabulator CDN)
  - API `/api/daily/grid-data` + `/api/daily/grid-save` (batch save เฉพาะคอลัมน์ที่กำหนด)
- [done] apply handoff `EMAIL_OAUTH_DRAFT_DAILY_GRID_V2_TH.md` ครบ:
  - เพิ่ม OAuth service `app/services/email_oauth.py` + route `/email/oauth/start|callback`
  - ขยาย `email_ingest` รองรับ `EMAIL_IMAP_AUTH=password|oauth2` + XOAUTH2
  - Inbox action `สร้างร่าง Daily` + daily save link กลับ `InboxEmail.linked_daily_job_id`
  - ขยาย Daily Grid ใกล้ parity กับ Daily form + filter `status/limit` + ซ่อน/แสดงคอลัมน์ด้วย localStorage
- [done] ปรับ `/daily/grid` ให้พร้อมใช้งาน single-page Daily workflow มากขึ้น:
  - เพิ่ม quick presets `BigC/LCB/AYU เดือนนี้`, `งานจริง/ลา/placeholder เดือนนี้`
  - Save เฉพาะ field ที่แก้จริง ลดความเสี่ยง overwrite ทั้งแถว
  - เพิ่ม unsaved warning, dirty-cell highlight, save feedback/errors, และลิงก์แก้เต็มรายแถว
- [done] ปรับ preset `/daily` + `/daily/grid` ให้ยึดรอบ payroll ต่อไซต์แทนเดือนปฏิทิน:
  - AYU ใช้รอบ `26->25`
  - LCB ใช้รอบ `16->15`
  - BIGC ใช้เดือนวิ่งแบบ `T-1` (`1->สิ้นเดือน` ของเดือนก่อนหน้า)
  - ปรับ label ปุ่ม preset ให้สื่อชัดว่าเป็นรอบ payroll
- [next] ทำ config จริงสำหรับ mailbox production (IMAP/OAuth2) + runbook setting env
- [done] เพิ่มปุ่ม “สร้างร่าง Daily จากอีเมล” โดยยังคง human-confirm + preflight ก่อนบันทึก
- [next] ทดสอบ OAuth จริงกับบัญชี Google production (consent screen + refresh token) แล้ว verify `/email/inbox/sync` ด้วย mailbox จริง
- [next] ประเมินการขยาย grid ไป `/petty-cash` แบบคอลัมน์จำกัดและไม่ข้าม guardrail รอบเงิน

## 2026-05-08 CC review follow-up (Email Inbox/OAuth/Draft Daily)

- [done] รับรองบันทึกผลตรวจจาก Claude Code แล้ว: อ่านโค้ดจุดเสี่ยง Email Inbox/OAuth/Draft Daily/Grid + route ที่เกี่ยวข้องครบ
- [done] รับรองผล verify จาก CC แล้ว: `py_compile` ผ่าน, `run_payroll_test.py` ผ่าน, `dmy_hm` filter register ถูกต้อง, และ flow `draft-daily -> daily_form -> daily/new` เชื่อม `inbox_mail_id` ได้
- [next] รอคำตอบผู้ใช้ 2 จุดก่อนแก้โค้ดต่อ:
  1) ต้องแสดง flash banner หลัง sync ว่า synced กี่ mails หรือไม่
  2) หลังบันทึก daily จาก inbox ให้ auto mark linked ทันทีหรือคงให้ผู้ใช้กดยืนยันอีกขั้น
- [next] หลังได้คำตอบ 2 ข้อด้านบน ค่อยแก้ `POST /daily/new` ให้ auto-linked ตาม policy ที่ยืนยัน (scope ไม่กระทบ payroll)
- [next] ประเมินความเสี่ยง CDN ใน `/daily/grid` (Tabulator): ถ้าต้องรองรับ offline ให้เตรียม fallback asset ภายในโปรเจกต์หรือกำหนดนโยบายว่า online-only อย่างเป็นทางการ

## 2026-05-08 Transport Rate Calculator deploy sync (GitHub Pages)

- [done] sync ไฟล์ deploy path: คัดลอก `ProjectYK_System/TransportRateCalculator/transport_rate_calculator.html` -> root `index.html` เพื่อให้หน้า Pages ใช้โค้ดล่าสุด (มีปุ่ม `Export CSV ตารางย้อนหลัง` + `exportHistoricalCsv()`)
- [done] push `origin/main` สำหรับ commit ที่แตะ `index.html` เพื่อแก้เคสหน้าเว็บไม่เห็นปุ่ม Export CSV ตารางย้อนหลัง
- [next] หลัง push รอ GitHub Pages deploy/cdn cache ประมาณ 1-5 นาที แล้ว hard refresh (`Ctrl+F5`) หน้า `https://yk-logistics.github.io/transport-rate-calculator/`

## 2026-05-08 GitHub Pages submodule checkout failure fix

- [done] ตรวจ Actions run ล่าสุดแล้วระบุ root cause ชัดเจน: fail ที่ `Checkout` ด้วยข้อความ `No url found for submodule path 'transport-rate-calculator-repo' in .gitmodules`
- [done] แก้ใน repo `yk-logistics/transport-rate-calculator`: ลบ gitlink mode `160000` path `transport-rate-calculator-repo` และ push `main` (commit `0243b51`)
- [done] ตรวจซ้ำ run ใหม่ `25546755229` พบว่า step `Checkout` ผ่านแล้ว (ไม่ติด error เดิม)
- [done] ยืนยันหน้า Oatside live หลัง deploy ล่าสุดแล้ว: `reports/oatside-pg-2026/index.html` แสดง pricing rules ชุดใหม่ (fuel-linked) พร้อม cache-bypass query (`?nocache=commit-e4516e9`)

## 2026-05-08 Oatside publish verification (summary page)

- [done] ระบุหน้า “รวมทั้งหมด” ที่ใช้งานจริง: `https://yk-logistics.github.io/transport-rate-calculator/reports/oatside-pg-2026/index.html`
- [done] rerun build + deploy + push ใหม่ด้วย `deploy_oatside_report.ps1 -RepoPath transport-rate-calculator-repo -Push` ได้ commit `e4516e9`
- [done] ตรวจหน้า live ทั้ง `index.html` และ `trips.html` แบบปกติและ cache-bypass แล้วว่าขึ้นราคาใหม่ชุดเดียวกับ Oatside ล่าสุด
- [done] แก้ mapping guardrail คอลัมน์ `Downtime_50_baht`/`Downtime_100_baht` ใน `Oatside/build_oatside_reports.py` พร้อม regression check `_assert_pricing_bucket_mapping(...)` กันค่าสลับช่องเงียบๆ
- [done] เปลี่ยนชื่อคอลัมน์ชีต `Trips_Pricing_All` ให้ตรงธุรกิจ: `Downtime_50_baht`, `Downtime_100_baht`, `Blank_run_50_baht`, `Return_job_baht`
- [done] rebuild + publish deploy อีกครั้งสำเร็จที่ commit `a0677c7` และยืนยัน summary น้ำมัน `exact=37, carry_forward=68, base_fallback=0`
- [done] hotfix หน้ารายงาน `trips.html`/`plates/71-5042.html`: ย้ายยอดแถว `71-5042` วันที่ `2026-04-21` จากคอลัมน์ `เสียเวลา+50%` ไป `เสียเวลา+100%` ตามการตรวจหน้างานของผู้ใช้ (ยอด `6,546.00`)
- [done] ลบ debug instrumentation ชั่วคราวออกจาก `Oatside/build_oatside_reports.py` หลังผู้ใช้ยืนยัน issue fixed และลบไฟล์ helper debug ที่ราก repo


- [done] ยืนยันกับผู้ใช้แล้วว่า policy เรท Oatside ช่วง `12-15 เม.ย. 2026` ต้องเป็น `8,000` (Base rate `50.00-50.99`) และล็อกเป็น fact ใน context เพื่อใช้ตรวจรอบถัดไป
