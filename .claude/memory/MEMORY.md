# Memory Index

## กฎยืน (อ่านก่อนทุกงาน)
- [🟢 มอบอำนาจเต็มแพลน MVP](project-jul3-session-close.md) — โอ 3ก.ค.: ลุยทุกงานในแพลนไม่ต้องรออนุมัติ ทำก่อนแก้ทีหลัง จดข้อสมมติ; กฎเงิน/ทำลายล้างยึดเดิม
- [⚠️ Fable ถึง 7/7 + เฟส P](project-fable-deadline-and-phase-p.md) — งานเงิน/ออกแบบยากให้ Fable ก่อน 7ก.ค. + ทิ้ง runbook ให้ Opus
- [🧠 วิธีคิด Fable→Opus](project-fable-mindset-doc.md) — docs/FABLE_MINDSET_FOR_OPUS.md โมเดลใหญ่ตัวถัดไปอ่าน 1 ครั้งเซสชันแรก (8 นิสัย+จังหวะต่องาน)
- [แพลน MVP](project-master-plan-jul26.md) — docs/MASTER_PLAN_2026-07.md + MVP_TASK_SPECS.md + PLAN_STATUS.json (อัปเดต%+scp ทุกครั้งที่จบงาน)
- [กฎ: ใช้เวลาจริง](feedback-use-real-clock.md) — Get-Date ก่อนพูดถึงเวลาเสมอ ห้ามเดา
- [กฎ: คู่มือส่งต่อโมเดลเล็ก](feedback-handoff-for-smaller-models.md) — ทุกงานทิ้ง runbook ให้ Haiku/Sonnet ทำต่อได้
- [กฎ: gsheet ถามก่อน+note ทุกช่อง](feedback-gsheet-edit-ask-and-comment.md) — ห้ามแก้ Sheet พลการ
- [กฎ: สลิป mao น้ำมันต้อง reconcile](feedback-slip-fuel-must-reconcile.md) — fuel_slip_reconcile.py; ย้ายน้ำมันแก้ 2 ที่
- [Concise, no code dump](feedback-concise-no-code-dump.md) — สรุปสั้นภาษาคน ซ่อนคำสั่ง/โค้ด/path เว้นแต่โอขอ
- [Keep working autonomously](feedback-keep-working-autonomously.md) — ตอบแทนโอแล้วไปต่อ; หยุดเฉพาะ เงิน/ทำลายล้าง/ออกนอก/จ่ายเงิน/ทางแยกจริง
- [Merge+deploy without preview](feedback-merge-and-deploy-without-preview.md) — งาน display จบ→merge→deploy ในเซสชันเดียว
- [git add -A อันตราย](feedback-git-add-all-danger.md) — stage เฉพาะ path ที่ตั้งใจ (เคยลาก DB backup 1.7GB)
- [Test-data cleanup safety](feedback-test-data-cleanup-safety.md) — ลบ test row ด้วย id ที่ได้คืนเท่านั้น ห้าม filter
- [Delegation ladder](feedback-delegation-qwen-then-haiku.md) — recon อ่านเยอะ→Qwen ฟรีก่อน→Haiku; เงิน/ตัดสินใจอยู่ตัวหลัก ([พื้นฐาน](feedback-qwen-and-subagent-cost.md))

## สถานะเงิน/รอบปัจจุบัน
- [ปิดรอบ มิ.ย. 3 ไซท์แล้ว](project-jun-close-3sites.md) — 3ก.ค. finalize LCB#2 287,711.37 / AYU#18 263,793.34 / BIGC#4 132,031.03; **รอบ finalized ห้าม recompute (สดย่อยหาย)**; ราคาแก้ทีหลัง→กลไกตกหล่น C4
- [ปิดเซสชัน 2-3ก.ค.](project-jul3-session-close.md) — deploy 11 อย่าง; ค้างถามโอ: ตัวอย่างใบเสร็จ/ใบหัก (A2) + Editor Drive (S1)
- [ปิดเซสชัน 1ก.ค.](project-jul1-session-close.md) — LCB#2/BigC#4 บน server; **local DB stale ห้าม push**
- [LCB+BigC มิ.ย. review](project-lcb-bigc-jun-payroll-review.md) — reconcile เป๊ะ; server LCB#2 ahead ของ local; เกศศักดิ์/ธนวัฒน์ = HR ไม่ใช่บั๊ก
- [LCB CY KB กติกาสุดท้าย](project-lcb-cy-kb-fulls.md) — คนขับคิดจากราคาคีย์ (kb=5000−คีย์) ส่วนต่างเข้าบริษัท; KB เจ้าของงาน=จากไฟล์
- [BigC มิ.ย. deposit/ภาษี/น้ำมัน](project-bigc-jun-deposit-tax-fuel.md) — ภาษี BigC รอโอตัดสิน

## งานเสร็จล่าสุด (ก.ค.)
- [🗄️ ประวัติซ่อม 2018-2026 เข้าระบบแล้ว](project-rm-history-backfill-done.md) — 10ก.ค. 8,237 บิล/16.67M จาก RM History sheets (v50); ยอดบนชีทเชื่อไม่ได้ (SUBTOTAL ค้าง ~6.1M มองไม่เห็น); ตกค้าง 00-0000 + รถป้ายอักษรไทย; กล่องบิล OCR = สเปคแล้วรอเขียน
- [🧾 บิลซ่อมรายการๆ + 📷 OCR](project-maint-bill-lines-ocr.md) — 9ก.ค. v49 deploy: MaintPart.kind (อะไหล่/ค่าแรง/บริการ) + /maint/records/{id}/read-bill ให้ sonnet อ่านรูปบิล → ร่าง กดยืนยันถึงเขียน DB; **รอโอลองบิลลายมือ**
- [🔎 กล่องรอคัดไลน์ไม่ตายเงียบ](project-todo-scan-claude-fallback.md) — 9ก.ค. Qwen gateway ล่ม content ว่างทุก prompt → ตก Claude haiku (เพดาน 8 ก้อน) + retry 1 ชม. + แบนเนอร์เตือน; log กรอง noise asyncio
- [🔒 แก้ cookie ขาด Secure 2 จุด](project-cookie-secure-fixes.md) — 8ก.ค. TDD **จบทั้งคู่ deploy live** verified: ① driver session (8e6b709) scp ตรง ② oauth_state (main.py:2537) ขึ้นพร้อมยาง v48 (server schema=48 + secure=_secure_cookies live + HEALTH 200); ทุก cookie มี Secure ครบบน HTTPS; gotcha _secure_cookies freeze ตอน import
- [🛞 ระบบยาง หยุดเลือด](project-tire-stop-the-bleed.md) — DONE+**deploy เขียว** 8ก.ค. (43a8a57, v48): คีย์บิลเร็ว `/maint/tires/bill` + รายงาน `/maint/tires/report` (เทียบหล่อ/แท้ บาท/เดือน·บาท/กิโล); ไม่บังคับไมล์; **รอโอลองคีย์บิลจริง 2-3 ใบ**
- [🧮 โต๊ะเช็คดีล /quote/deal](project-deal-checker.md) — DONE+deploy 6ก.ค. (v47): วางรูทลูกค้าทั้งก้อน→ต้นทุน/กำไร/ราคาเสนอ+ผันน้ำมัน; DealRecord+PlaceCache; gotcha: literal path ใต้ /quote ต้องมาก่อน /quote/{qid}
- [🚚 เครื่องคิดต้นทุน Wonder Sub 2026](project-wonder-sub-cost-calculator.md) — 51 จว. (6/10 ล้อ) ราคาผันน้ำมัน+OSRM; **เข้าแอปแล้ว `/quote/wonder`**; ค้างถาม: ขากลับมีของไหม
- [🏁 ปิดเซสชัน 6ก.ค. + ส่งไม้ Opus](project-jul6-session-close.md) — Drive backup จบ (drive_ok=true) · AYU ก.ค. 314 งานเข้าระบบ · วันจ่ายจริง LCB/BIGC=1 AYU=สิ้นเดือน · บัญชีทีม 7 คน (รอโอแจกรหัส+เปลี่ยน yk1) · **งานเงิน/ออกแบบยากหมดเกลี้ยง; งานปฏิทินถัดไป = ปิดรอบ LCB 15ก.ค. ตาม runbook**
- [สลิป k-tag ตารางลูกผสม + ธงน้ำมัน E2](project-slip-ktag-mixed-table.md) — DONE 5ก.ค. deploy เขียว: ป้ายเหมา/เที่ยว/รถจอด + พิเศษ/OT + ⚠ ธงน้ำมันผิดปกติ (R1 ≥3 บิล/วัน กันคู่ B7+B20); **บล็อก "ห้ามทับ template สลิป" ยกเลิกแล้ว**
- [🧪 TradeLab บอทเทรดเงินสมมุติ](project-tradelab-paper-bot.md) — นอก repo: trade.yklogistics.uk; v2 (regime ADX + ATR stop + F&G + AI ข่าว) แข่ง v1/v2/hold; เกณฑ์: ชนะ buy&hold 1-3 เดือนค่อยคุยต่อ; **ห้ามปนงานเงิน YK**
- [PWA icon /todo ลง Taskbar](project-pwa-todo-taskbar-icon.md) — DONE 5ก.ค. (542e806) hunk PWA เข้า HEAD แล้ว; รอโอลบ shortcut เก่า+Install ใหม่
- [LINE→todo + AI จบครบ 4 เฟส](project-line-to-todo-ai-phases.md) — 5ก.ค. v46: /line→/todo · ✨ Qwen เรียบเรียง (สำรอง Claude) · หน้า /ai แชท · 📥 กล่องรอคัดจากไลน์ (วัดจริง 49 งาน); docs/AI_CHAT_RUNBOOK.md; gotcha 9arm REST: /v1/chat/completions + ตั้ง UA เอง
- [AYU ก.ค. ✅ import แล้ว](project-ayu-jul-import-ready.md) — 314 งาน+60 น้ำมัน; **กติกา: AYU แก้ที่ชีทจริงเท่านั้น → re-import --wipe-prior; ห้าม wipe ถ้าเริ่มแก้ grid**
- [🚀 Starlette migrated](project-starlette-migrated.md) — 4ก.ค.: fastapi 0.139/starlette 1.3.1, 0 CVE; **route ใหม่ต้อง TemplateResponse(request, name, ctx)**
- [F4 น้ำมันไลน์↔ระบบ](project-f4-fuel-line-compare.md) — DONE 4ก.ค. ไม่ใช้ OCR: /fuel/line-compare parse ข้อความแจ้งเติม; ตกหล่นจริง 7 รายการรอทีม
- [☀️ เซสชันกลางวัน 4ก.ค.](project-jul4-day-run.md) — G2/S3/F0/S5 done + F3 จูน + doc_no clean 208 + CVE multipart → แพลน 34/38
- [🌙 คืน 3→4ก.ค. มาราธอน 22 งาน](project-jul4-night-run.md) — แพลน 31/38 (82%) deploy v42: C2/P1/P2/P3/P5/D2/D3/E1 (PWA เช็คอิน)/E2/F2 (วัดจริง 1,256 ข้อความ)/F3/F5/S2/S4/S5/A5/B1.1; **7 งานเหลือติดเงื่อนไขภายนอกหมด**
- [G2 ย้ายรูปลงแผ่น External](project-g2-media-archive.md) — DONE 4ก.ค. v44: copy→hash→ลบ + ป้าย EXT-xx บน /line; รอโอเสียบแผ่นจริง
- S3 DONE 4ก.ค. — docs/SECRETS_INVENTORY.md ทะเบียน 7 secret + หมุน SLIP_INGEST_TOKEN จริงแล้ว; rotate LINE/Discord/Anthropic/SA รอ console โอ
- [F3 POD วัดจริง+จูนแล้ว](project-f3-pod-measured-tuned.md) — reverse-match เลข Job (strong 57→80); LineGroupMap 38 กลุ่มลง server; NHL ต้อง OCR
- [C2 ออกใบวางบิล](project-c2-invoice-builder.md) — /billing/invoice CY+KMMT+CJ verified 6 ใบจริง; runbook INVOICE_BUILDER_SPEC.md; ไม่เขียน invoice_no กลับเดลี่
- [C4 ค่าเที่ยวตกหล่น](project-c4-pay-adjustment.md) — DONE 3ก.ค.: แก้ tfd รอบปิด→ตั้งยอดอัตโนมัติ→บวก/หักรอบถัดไป idempotent (v36)
- [B3 ราคาใบเสนอ→เดลี่](project-b3-quote-to-daily.md) — ปุ่ม 💡 ใน grid กดรับต่อแถว (ไม่ทับ+audit) + /billing เตือนราคา≠ใบเสนอ
- [S1 สำรอง 4 ชั้นครบ](project-s1-backup-3tier.md) — nightly zip→D: + External + Dev mirror + Discord + Drive (drive_ok=true 6ก.ค.) + ซ้อมกู้
- [C1 พร้อมวางบิล?](project-c1-billing-ready.md) — แถบเช็คใน /billing (ราคาว่าง/ไม่มีเลขใบงาน/ตู้ซ้ำ); helper _daily_row_kind ใช้ร่วมปฏิทิน
- [B2 เซฟใบเสนอราคา](project-b2-quote-save.md) — /quote/sync พูดโปรโตคอล Drive-sync เดิม + /quote/list v35
- [B4 ปฏิทินกำลังรถ /calendar](project-b4-fleet-calendar.md) — ว่าง=รวม−จอง/วิ่ง−ซ่อม−ลา; GOTCHA เดลี่ไม่มี vehicle link ต้อง match ทะเบียนข้อความ
- [KB payout /kb-payout](project-cy-kb-payout-calculator.md) — จับคู่ยอดโอน 4 เจ้า + ติ๊กรับ (KbSettle v32); runbook docs/KB_PAYOUT_RUNBOOK.md
- [หน้ารอรับเงินลูกค้า AR](project-receivables-page.md) — /finance/receivables อ่านทะเบียนรับเช็คจาก Drive แท็บ 2026+
- [สลิป 3 surface](project-slip-surfaces-consistency.md) · [สลิปคนเหมา KB reconcile](project-slip-mao-kb-reconcile.md) — รายคน/ZIP=payroll_slip, /print=print_all; KB dispatch ตาม pay_mode ทุก surface
- [เครื่องมือกู้รหัส MVP](project-mvp-reset-password-tool.md) · [DB swap ทับรหัสผ่าน](project-mvp-password-db-swap-gotcha.md) — RESET_PASSWORD.bat; swap DB ต้อง preserve appuser hash จาก server ก่อน
- [ย้ายข้อมูลพี่หวาน xlsx→ชีท AYU](project-ayu-sync-wan-xlsx.md) — runbook+สคริปต์ tools/wan_sheet_sync/

## งานเสร็จ 29-30 มิ.ย. (payroll มิ.ย. + สลิป)
- [Daily grid Save ไม่ติด](project-daily-grid-save-auth-redirect.md) — commitOpenEditor ก่อน Save + 401 JSON แทน redirect เงียบ
- [LCB เหมา จ่ายต่อเที่ยว](project-lcb-mao-pertrip-pay.md) — lcb_mao=Σtrip_fee_driver (เลิก revenue×60%) · [AYU เหมา](project-ayu-mao-pertrip-pay.md) — ayu_mao=Σtrip_fee_driver
- [ปรีชา สดย่อย 4,095](project-preecha-petty.md) — คนใหม่ onboard หลัง petty import ต้องดึงตาม
- [AYU office reconcile ตามรูป](project-ayu-office-reconcile-rup.md) — รูปเงินเดือน=ground truth · [AYU office SS 9 คน](project-ayu-office-ss.md) — ค้าง onboard ซองอู/พร/จอมิน/เก้า + แม่บ้านใหม่
- [ธัชชนพล น้ำมัน +2 ยอด](project-thach-fuel-jun.md) — ยอดติดลบ=คืนน้ำมัน
- [เรวัตร น้ำมัน handover 1/6](project-rewat-handover-fuel-jun.md) — probe_db.py เทียบ local↔server ก่อน push (โอกำชับ)
- [สลิปรวมน้ำมันเติมรอบเดียว B7+B20](project-slip-merge-fuel-same-fill.md) — display-only key=FuelTxn.txn_date
- [fix grid header filter](project-grid-header-filter-fix.md) — Tabulator ต้อง refreshFilter() หลัง success()
- [LCB deposit sync SSO](project-lcb-deposit-sso-resync.md) — "X/10"=จ่ายครบ X งวด → balance=X×1000
- [AYU มิ.ย. payroll](project-ayu-jun-payroll.md) — recompute ลบ office copy ต้อง re-copy · [AYU daily import](project-ayu-daily-import.md) — รอบ 26→25
- **คน/ยอดรายคน:** [บัญชีโอน+ป้าไก่+เรืองฤทธิ์](project-transfer-bank-fix-paikai-ruangrit.md) · [ยอดโอนรวม=net>0](project-transfer-total-positive-only.md) · [AYU deposit+พิมพ์สลิป](project-ayu-deposit-installments.md) · [ช่างน้อย+ศราวุธ](project-ayu-office-changnoi-sarawut.md) · [AYU คนใหม่ 4 คน](project-ayu-jun-new-drivers.md) · [ชัชวาล การันตี 15,000](project-chatchawal-guarantee.md) · [สดย่อยสมัย แยกไซท์](project-samai-petty-split-ayu-bigc.md) · [ธัชชนพล deposit 2,000](project-thach-deposit-2000-hold.md) · [ออฟฟิสไม่หักประกันตน](project-office-no-deposit.md)
- **สลิป มิ.ย.:** [handover_manual offtable](project-slip-handover-manual-offtable.md) · [น้ำมันตามวันเติมจริง](project-slip-fuel-fill-date.md) · [โชว์น้ำมันนอกตาราง](project-slip-offtable-fuel-display.md) · [งานยกเลิกไม่รั่ว remark](project-slip-cancel-remark-leak.md) · [1 คน = 1 หน้า](project-slip-one-page-per-driver.md) · [ลิตร+หักจริง/ไม่หัก](project-slip-fuel-deduct-clarity.md) · [route เต็ม](project-slip-route-display.md) · [แจกแจงสดย่อย](project-payroll-slip-petty-itemize.md) · [ZIP แยกคน](project-payroll-slip-zip-per-driver.md)
- **ไซท์/น้ำมัน:** [น้ำมัน 23/6 ย้าย 0556→0560](project-fuel-move-0556-0560.md) · [น้ำมัน B7/B20 เกรด](project-fuel-b7b20-grade.md) · [BigC วันหยุด+อนุโลม](project-bigc-holiday-anuloom.md) · [Jun payroll AYU+BIGC status](project-jun-payroll-ayu-bigc-status.md) · [LCB deposit screenshot](project-lcb-deposit-jun-screenshot-reconcile.md) · [LCB มิ.ย. audit รอบ 2](project-lcb-jun-audit-round2.md) · [LCB driver extra fees](project-lcb-driver-extra-fees.md) · [AYU-Yusen 60% (PAUSED)](project-ayu-yusen-charter-pay.md)

- [🗡️ SpiritVale codex (นอก repo YK)](project-spiritvale-codex.md) — 9ก.ค. เก็บ baseline ก่อน EA (15ก.ค.) แล้ว; **gotcha: Paladin มาจาก Knight ไม่ใช่ Acolyte → HP archetype 100% vs 75%**; ค้างรายงานเทียบ 8 อาชีพ

## เครื่องมือ/อ้างอิงเทคนิค
- [🧪 แอปมี test suite จริง 545 tests](project-app-has-test-suite.md) — pytest ที่ app/tests/ (CLAUDE.md เคยบอกผิดว่าไม่มี); รันด้วย -X utf8 -p no:cacheprovider; conftest ใช้ throwaway SQLite
- [📕 Runbook ปิดรอบเงินเดือน](reference-payroll-close-runbook.md) — docs/PAYROLL_CYCLE_CLOSE_RUNBOOK.md ให้โมเดลถัดไปปิดรอบ LCB 15ก.ค. เองได้ (กฎเหล็ก+checklist+gotcha)
- [ไอเดียจาก Discord 9arm](reference-9arm-discord-ideas.md) — fallback Qwen→Claude ทำแล้ว; สลิปAPI/QR ไม่เอา; **gotcha: qwen-readonly ปนความจำ repo เราเข้าไปในคำตอบ — grep ยืนยันก่อนเชื่อ**
- [⏰ Task Scheduler ฆ่างานที่รันเกิน 72 ชม.](reference-scheduled-task-72h-kill.md) — TradeLab ดับ 9ก.ค. เพราะ default PT72H; แก้เป็น PT0S แล้ว 3 task (TRADELAB/MVP_APP/TUNNEL); พอร์ต 8010/8020/8030
- [⚠️ แอปรันเป็น SYSTEM — ทดสอบ claude ต้องในสิทธิ์ SYSTEM](reference-test-claude-as-system.md) — yklog มี WSL bash แต่ SYSTEM ไม่มี; ลง Git for Windows แก้แล้ว; ps1 ที่ scp ห้ามมีภาษาไทย
- [🖼️ claude -p อ่านรูปได้](reference-claude-cli-reads-images.md) — ใส่ path ในโปรมต์ + Read tool = OCR ในแอป (Qwen รับแต่ text); ใช้ใน services/bill_ocr.py
- [⚡ effort max ตั้งยังไง](reference-claude-effort-max.md) — `echo $CLAUDE_EFFORT` เช็คได้; settings.json เก็บ max ไม่ได้ (เพดาน xhigh) ต้อง `--effort max` ตอนเปิด; pwsh profile inject ให้แล้ว
- [Deploy MVP self-verify](reference-deploy-mvp-selfverify.md) — DEFAULT: deploy_mvp.sh --markers "<ascii>" (แต่ copy ทั้ง dir — มีไฟล์ session อื่นค้างให้ surgical scp แทน)
- [net_guard ทุกไซต์](reference-net-guard.md) — net_guard.py before/after --allow <ids> พิสูจน์รอบอื่นนิ่ง
- [Chrome headless PDF](reference-chrome-headless-pdf.md) — --user-data-dir + poll ไฟล์ + ห้าม TemporaryDirectory; ตัดสินไทยด้วย screenshot
- [Google Drive access](reference-google-drive-access.md) — service acct + Drive API; list ทีละชั้น · [Google Sheets](reference-google-sheets-access.md) — gspread; open_by_key เท่านั้น; 60 reads/min
- [Deploy ผ่าน Tailscale](reference-deploy-via-tailscale.md) — yklog@100.97.150.114; quote ซ้อนพัง→scp .ps1 ไปรัน
- [MVP server deploy](reference-mvp-server-deploy.md) — app.yklogistics.uk; runbook MVP_SERVER_DEPLOY.md
- [MVP deploy restart gotcha](reference-mvp-deploy-restart-gotcha.md) — kill by 8010-PID ไม่ใช่ filter .venv (โดน archiver)
- [Branch flips mid-session](reference-branch-switch-during-session.md) — เช็ค git branch --show-current ก่อน mutation
- [LINE archiver](reference-line-archiver.md) — service แยก port 8020; line_archive.db + line_media/
- [yklogistics.com DNS](reference-yklogistics-dns.md) — A/MX/SPF ห้ามหาย · [SSH to YK machine](reference-ssh-to-yk-machine.md) — passwordless yklog; LAN+Tailscale
- [Server no GPU](reference-server-no-gpu-llm.md) — ห้าม self-host LLM บน .197
- [Window-warm routines](reference-window-warm-routines.md) — 4 routines เปิด usage window 06/11/16/21 BKT
- [Windows vs Linux stack](reference-windows-vs-linux-stack-choice.md) — setup ของโอถูกแล้ว อย่าเสนอย้าย
- [Auto-resume system](reference-auto-resume-system.md) — resume-after-limit hook+watcher
- [Qwen subagent](reference-qwen-subagent.md) — qwen.ps1 recon ฟรี read-only · [Superpowers + 9arm](project-superpowers-9arm-models.md) — 9arm Qwen แยก config ห้ามงานเงิน
- [HOME pwsh setup](reference-home-pwsh-terminal-setup.md) — ใช้ Windows Terminal กันวรรณยุกต์หาย
- [Makcu macro_engine](reference-makcu-macro-engine.md) — ของส่วนตัวโอ นอก repo YK · [YT summarize](reference-yt-summarize.md) — yt-dlp captions → Qwen สรุปไทย
- [Claude Code installs](claude-code-multiple-installs.md) — ตัวไหนรันจริงบนเครื่องโอ

## ประวัติ/โดเมน (มิ.ย. และก่อนหน้า)
- [KB + ราคาคำนวณคนขับ](project-kb-driver-calc-price.md) — driver_calc_price=(override??rev)−kb
- [BigC คอลัมน์ E = ลูกค้า](project-bigc-column-e-customers.md) — 1/2+BH/DV/++=บิ๊กซี
- [BigC พ.ค. payroll](project-bigc-may-payroll.md) — เดือน มิ.ย.=วิ่ง พ.ค.
- [CFO cycle vs calendar](project-cfo-cycle-vs-calendar.md) — /finance สลับ เดือน↔รอบจ่าย
- [รถร่วม บุญนาม TODO](project-rojruam-bunnam-todo.md) — รอโอยืนยันสูตร 13%
- [DHL คืนไฟล์ตรวจบิล Oatside มิ.ย.](project-oatside-jun-dhl-checkback.md) — IV2606-020: gap +55,392 (เรา 1,375,776 vs DHL 1,320,384) แยก 3 หมวด; P/R/T/W=เรา Q/S/U/X=DHL
- [LCB daily↔fuel cross-check](project-lcb-daily-fuel-crosscheck.md) — tool พร้อม รอ archive สะสมข้อมูล · [กติกา cross-check](project-lcb-fuel-crosscheck-domain-rules.md) — เติมข้ามไซท์=ปกติ
- **LCB:** [daily sheet](project-daily-lcb-sheet.md) · [mixed mode](project-lcb-mixed-mode.md) · [mixed idle-days](project-lcb-mixed-idle-days.md) · [Jun xlsx reimport](project-lcb-jun-xlsx-reimport.md) · [พ.ค. lock ตาม PDF](project-lcb-may-lock-pdf.md) · [slip-reader](project-lcb-slip-reader.md)
- **น้ำมัน:** [exclude-from-driver](project-fuel-exclude-from-driver.md) · [Mao วัดถัง 2 กฎ](project-mao-fuel-tank-measure.md) · [handover-measure BACKLOG](project-fuel-handover-measure-backlog.md) · [pump reconcile](project-fuel-pump-reconcile.md)
- **เงินเดือน/บิล:** [Deposit งวด X/Y](project-deposit-installment-number.md) · [Deposits overview](project-deposits-overview-page.md) · [Driver pay breakdown](project-driver-pay-breakdown-daily-slip.md) · [Payroll bank + print](project-payroll-bank-print.md) · [Multi-site payroll onboard](project-multisite-payroll-onboard.md) · [DHL Overflow rate](project-dhl-overflow-rate.md) · [BigC daily import](project-bigc-daily-import.md)
- **อื่นๆ:** [CFO revenue drill-down](project-cfo-revenue-drilldown.md) · [Oatside billing recon](project-oatside-billing-recon.md) · [Oatside report UI](project-oatside-report-ui-edits.md) · [UPS power-alert](project-ups-power-alert.md) · [Daily grid edit UX](project-daily-grid-edit-ux.md) · [Merge Daily + Grid](project-merge-daily-grid.md)
