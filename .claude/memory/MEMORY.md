# Memory Index

## กฎยืน (อ่านก่อนทุกงาน)
- [🟢 มอบอำนาจเต็มแพลน MVP](project-jul3-session-close.md) — โอ 3ก.ค.: ลุยทุกงานในแพลนไม่ต้องรออนุมัติ จดข้อสมมติ; กฎเงิน/ทำลายล้างยึดเดิม
- [⚠️ Fable หมดเขต ≈13ก.ค. 14:00 ไทย](project-fable-deadline-and-phase-p.md) — หลังนั้น Opus; ทุกงานทิ้ง runbook
- [🧠 วิธีคิด Fable→Opus](project-fable-mindset-doc.md) — docs/FABLE_MINDSET_FOR_OPUS.md อ่าน 1 ครั้งเซสชันแรก
- [🧰 ชุดเครื่องมือ Opus](project-opus-toolkit.md) — สกิล 3 ตัว .claude/skills + หมวด "โหมด Opus" ใน CLAUDE.md — trigger เอง
- [แพลน MVP](project-master-plan-jul26.md) — PLAN_STATUS.json อัปเดต%+scp ทุกครั้งที่จบงาน
- [กฎ: ใช้เวลาจริง](feedback-use-real-clock.md) — Get-Date ก่อนพูดถึงเวลา ห้ามเดา
- [กฎ: runbook ให้โมเดลเล็ก](feedback-handoff-for-smaller-models.md) · [กฎ: gsheet ถามก่อน+note](feedback-gsheet-edit-ask-and-comment.md) · [กฎ: สลิป mao reconcile](feedback-slip-fuel-must-reconcile.md) — ย้ายน้ำมันแก้ 2 ที่
- [Concise, no code dump](feedback-concise-no-code-dump.md) — สรุปสั้นภาษาคน ไม่โชว์โค้ด/path เว้นแต่โอขอ
- [Keep working autonomously](feedback-keep-working-autonomously.md) — หยุดเฉพาะ เงิน/ทำลายล้าง/จ่ายเงิน/ทางแยกจริง
- [Merge+deploy without preview](feedback-merge-and-deploy-without-preview.md) — งาน display จบ→deploy เซสชันเดียว
- [git add -A อันตราย](feedback-git-add-all-danger.md) — stage เฉพาะ path (เคยลาก DB 1.7GB)
- [Test-data cleanup safety](feedback-test-data-cleanup-safety.md) — ลบ test row ด้วย id ที่ได้คืนเท่านั้น
- [Delegation ladder](feedback-delegation-qwen-then-haiku.md) — recon→Qwen ฟรีก่อน→Haiku; เงินอยู่ตัวหลัก ([พื้นฐาน](feedback-qwen-and-subagent-cost.md))

## สถานะเงิน/รอบปัจจุบัน
- [ปิดรอบ มิ.ย. 3 ไซท์แล้ว](project-jun-close-3sites.md) — finalize LCB#2 287,711.37 / AYU#18 263,793.34 / BIGC#4 132,031.03; **finalized ห้าม recompute**; แก้ราคาย้อนหลัง→กลไก C4
- [📋 Pre-close LCB 2026-07](project-lcb-jul-preclose-audit.md) — ✅ 12ก.ค.: ทีมคีย์ตามทัน (เดลี่ 10-11/7, สดย่อย 11/7) **พร้อมปิดรอบ 15/7**; เล่มสดย่อย LCB จริง = gsheet "สดย่อย LCB" แท็บชื่อรอบ; ค้างยืนยัน 21/6 อาทิตย์ว่าง
- [ปิดเซสชัน 1-3ก.ค.](project-jul3-session-close.md) — ([1ก.ค.](project-jul1-session-close.md) **local DB stale ห้าม push**)
- [LCB+BigC มิ.ย. review](project-lcb-bigc-jun-payroll-review.md) — เกศศักดิ์/ธนวัฒน์ = HR ไม่ใช่บั๊ก
- [LCB CY KB กติกา](project-lcb-cy-kb-fulls.md) — kb=5000−คีย์ ส่วนต่างเข้าบริษัท · [BigC มิ.ย. deposit/ภาษี](project-bigc-jun-deposit-tax-fuel.md) — ภาษีรอโอ

## งานเสร็จล่าสุด (ก.ค.)
- [🧾💰 v52 ทะเบียนใบวางบิล + v53 ใบเสร็จ 3 สถานะ](project-invoice-registry.md) — 12ก.ค. deploy (schema 53): สร้างใบ→ประทับเลขกลับเดลี่อัตโนมัติ + /billing/invoices issued→received→paid|void + เตือนเกิน due; petty มี/ไม่มี/รอ + ปุ่มได้ใบเสร็จแล้ว; แก้บั๊กแฝง petty_save driver_obj; ค้าง: เบิกรายสัปดาห์ LCB (docs/WEEKLY_ADVANCE_LCB_SPEC.md รอโอเคาะ 5 ข้อ)
- [📱 สแกนบิลมือถือโอ จบ](project-phone-bill-scan.md) — 10-12ก.ค.: 9,938 รูป → **กล่องบิล ready 306 ใบ = 3,789,714.72 บาท รอโอคัด**; ก.พ.219 พิสูจน์ไม่ซ้ำ RM (0/10); worker OCR task SYSTEM ใช้ซ้ำได้; กติกาโอ: IRISO/รพ./PTT ไม่เอา, เลขท้าย 8003=71-8003; gotcha MTP+claude -p+OAuth ใน start_mvp.bat
- [🧮 /quote ค้างค่าเดิม แก้แล้ว](project-quote-recalc-stale-fix.md) — 10ก.ค. (dcd1714); **ไฟล์คู่ app↔TransportRateCalculator ต้อง byte-identical**
- [🛠️ Oatside no_finish ตาม DHL](project-oatside-jun-dhl-checkback.md) — 10ก.ค. deploy; **ไม่ rebuild มิ.ย. บน server**; หมวด B = noise คงกติกาเดิม
- [🗄️ ประวัติซ่อม 2018-26 เข้าระบบ](project-rm-history-backfill-done.md) — 8,237 บิล/16.67M (v50); ยอดบนชีทเชื่อไม่ได้ (SUBTOTAL ค้าง)
- [🧾 บิลซ่อมรายการๆ + OCR](project-maint-bill-lines-ocr.md) — v49: ร่างจากรูป กดยืนยันถึงเขียน DB
- [🔎 กล่องรอคัดไลน์ fallback](project-todo-scan-claude-fallback.md) — Qwen ล่ม→haiku+retry+แบนเนอร์
- [🔒 cookie Secure ครบ](project-cookie-secure-fixes.md) — 8ก.ค. ทั้งคู่ live; gotcha _secure_cookies freeze ตอน import
- [🛞 ระบบยาง](project-tire-stop-the-bleed.md) — v48+v52: คีย์บิล/รายงานหล่อ-แท้ + **รายเส้นเลือกคัน/สต๊อก**; ยางจริง 2 เส้นแรก T0001-2 (ไทร์มาร์ท 71-8000); BR=บอสรับเบอร์
- [🧮 โต๊ะเช็คดีล /quote/deal](project-deal-checker.md) — v47; gotcha literal path ก่อน /quote/{qid}
- [🚚 Wonder Sub /quote/wonder](project-wonder-sub-cost-calculator.md) — ค้างถาม: ขากลับมีของไหม
- [🏁 ปิดเซสชัน 6ก.ค.](project-jul6-session-close.md) — Drive backup ok · บัญชีทีม 7 คน (รอโอแจกรหัส) · วันจ่าย LCB/BIGC=1 AYU=สิ้นเดือน
- [สลิป k-tag + ธงน้ำมัน](project-slip-ktag-mixed-table.md) — 5ก.ค.; บล็อกห้ามทับ template ยกเลิกแล้ว
- [🧪 TradeLab](project-tradelab-paper-bot.md) — นอก repo; **ห้ามปนงานเงิน YK**
- [PWA /todo Taskbar](project-pwa-todo-taskbar-icon.md) — รอโอ Install ใหม่
- [LINE→todo + AI 4 เฟส](project-line-to-todo-ai-phases.md) — v46; gotcha 9arm REST: /v1/chat/completions + UA เอง
- [AYU ก.ค. refresh 10ก.ค.](project-ayu-jul-import-ready.md) — **AYU แก้ที่ชีทจริงเท่านั้น → re-import --wipe-prior; ห้าม wipe ถ้าแก้ grid แล้ว**
- [🚀 Starlette migrated](project-starlette-migrated.md) — **route ใหม่ต้อง TemplateResponse(request, name, ctx)**
- [F4 น้ำมันไลน์↔ระบบ](project-f4-fuel-line-compare.md) · [☀️ 4ก.ค.](project-jul4-day-run.md) · [🌙 มาราธอน 22 งาน](project-jul4-night-run.md) — แพลน 34/38, ที่เหลือติดเงื่อนไขนอก
- [G2 รูปลงแผ่น External](project-g2-media-archive.md) — รอโอเสียบแผ่น · S3 secrets — rotate LINE/Discord/Anthropic/SA รอ console โอ
- [F3 POD จูนแล้ว](project-f3-pod-measured-tuned.md) — NHL ต้อง OCR
- [C2 ออกใบวางบิล](project-c2-invoice-builder.md) — (กติกา "ไม่เขียนเลขกลับ" ถูกแทนด้วย v52 แล้ว)
- [C4 ค่าเที่ยวตกหล่น](project-c4-pay-adjustment.md) · [B3 ราคาใบเสนอ→เดลี่](project-b3-quote-to-daily.md) · [S1 สำรอง 4 ชั้น](project-s1-backup-3tier.md) · [C1 พร้อมวางบิล](project-c1-billing-ready.md) · [B2 เซฟใบเสนอ](project-b2-quote-save.md) · [B4 ปฏิทินรถ](project-b4-fleet-calendar.md) — GOTCHA เดลี่ match ทะเบียนข้อความ
- [KB payout](project-cy-kb-payout-calculator.md) · [AR /finance/receivables](project-receivables-page.md) — อ่านชีท Drive (v52 ทะเบียนใหม่ยังแยกกัน)
- [สลิป 3 surface](project-slip-surfaces-consistency.md) · [สลิปเหมา KB](project-slip-mao-kb-reconcile.md) · [กู้รหัส MVP](project-mvp-reset-password-tool.md) · [DB swap ทับรหัส](project-mvp-password-db-swap-gotcha.md) — preserve appuser hash ก่อน swap
- [ย้ายข้อมูลพี่หวาน](project-ayu-sync-wan-xlsx.md) — tools/wan_sheet_sync/

## งานเสร็จ 29-30 มิ.ย. (payroll มิ.ย. + สลิป)
- [Daily grid Save](project-daily-grid-save-auth-redirect.md) · [LCB เหมาต่อเที่ยว](project-lcb-mao-pertrip-pay.md) · [AYU เหมา](project-ayu-mao-pertrip-pay.md) — Σtrip_fee_driver เลิก 60%
- [ปรีชา petty](project-preecha-petty.md) — onboard หลัง import ต้องดึงตาม · [เรวัตร handover](project-rewat-handover-fuel-jun.md) — probe_db.py เทียบ local↔server ก่อน push
- [AYU office reconcile](project-ayu-office-reconcile-rup.md) — รูปเงินเดือน=ground truth · [AYU office SS](project-ayu-office-ss.md) · [ธัชชนพล น้ำมัน](project-thach-fuel-jun.md) — ติดลบ=คืนน้ำมัน
- [สลิปรวมน้ำมัน B7+B20](project-slip-merge-fuel-same-fill.md) · [grid header filter](project-grid-header-filter-fix.md) — refreshFilter() หลัง success()
- [LCB deposit SSO](project-lcb-deposit-sso-resync.md) — "X/10"=จ่ายครบ X งวด · [AYU payroll](project-ayu-jun-payroll.md) — recompute ต้อง re-copy office · [AYU import](project-ayu-daily-import.md) — รอบ 26→25
- **คน/ยอดรายคน:** [บัญชีโอน](project-transfer-bank-fix-paikai-ruangrit.md) · [ยอดโอน=net>0](project-transfer-total-positive-only.md) · [AYU deposit](project-ayu-deposit-installments.md) · [ช่างน้อย+ศราวุธ](project-ayu-office-changnoi-sarawut.md) · [AYU ใหม่ 4 คน](project-ayu-jun-new-drivers.md) · [ชัชวาล 15,000](project-chatchawal-guarantee.md) · [สมัยแยกไซท์](project-samai-petty-split-ayu-bigc.md) · [ธัชชนพล 2,000](project-thach-deposit-2000-hold.md) · [ออฟฟิสไม่หักประกัน](project-office-no-deposit.md)
- **สลิป มิ.ย.:** [handover offtable](project-slip-handover-manual-offtable.md) · [น้ำมันวันเติมจริง](project-slip-fuel-fill-date.md) · [น้ำมันนอกตาราง](project-slip-offtable-fuel-display.md) · [ยกเลิกไม่รั่ว remark](project-slip-cancel-remark-leak.md) · [1 คน 1 หน้า](project-slip-one-page-per-driver.md) · [ลิตร+หักชัด](project-slip-fuel-deduct-clarity.md) · [route เต็ม](project-slip-route-display.md) · [แจกแจงสดย่อย](project-payroll-slip-petty-itemize.md) · [ZIP รายคน](project-payroll-slip-zip-per-driver.md)
- **ไซท์/น้ำมัน:** [ย้าย 0556→0560](project-fuel-move-0556-0560.md) · [B7/B20 เกรด](project-fuel-b7b20-grade.md) · [BigC วันหยุด](project-bigc-holiday-anuloom.md) · [Jun AYU+BIGC status](project-jun-payroll-ayu-bigc-status.md) · [LCB deposit screenshot](project-lcb-deposit-jun-screenshot-reconcile.md) · [LCB audit รอบ 2](project-lcb-jun-audit-round2.md) · [LCB extra fees](project-lcb-driver-extra-fees.md) · [AYU-Yusen (PAUSED)](project-ayu-yusen-charter-pay.md)
- [🗡️ SpiritVale (นอก repo)](project-spiritvale-codex.md) — Paladin จาก Knight ไม่ใช่ Acolyte; ค้างเทียบ 8 อาชีพ

## เครื่องมือ/อ้างอิงเทคนิค
- [📊 Claude Usage widget](reference-claude-usage-widget.md) — oauth/usage ต้องมี anthropic-beta header; IRM แปลง datetime เอง
- [🧪 test suite จริง 700+](project-app-has-test-suite.md) — รัน -X utf8 -p no:cacheprovider; throwaway SQLite
- [📕 Runbook ปิดรอบเงินเดือน](reference-payroll-close-runbook.md) — PAYROLL_CYCLE_CLOSE_RUNBOOK.md ปิด LCB 15ก.ค. เองได้
- [ไอเดีย 9arm](reference-9arm-discord-ideas.md) — **qwen-readonly ปนความจำ — grep ยืนยันก่อนเชื่อ**
- [⏰ Task เกิน 72 ชม.โดนฆ่า](reference-scheduled-task-72h-kill.md) — ตั้ง PT0S แล้ว; พอร์ต 8010/8020/8030
- [⚠️ แอป=SYSTEM](reference-test-claude-as-system.md) — claude ฝั่ง server ล็อกอินผ่าน OAuth token ใน start_mvp.bat; ps1 ที่ scp ห้ามมีไทย
- [🖼️ claude -p อ่านรูป](reference-claude-cli-reads-images.md) — Qwen รับแต่ text; ใช้ใน bill_ocr.py
- [⚡ effort max](reference-claude-effort-max.md) — ต้อง --effort max ตอนเปิด; pwsh profile inject แล้ว
- [Deploy self-verify](reference-deploy-mvp-selfverify.md) — deploy_mvp.sh copy ทั้ง dir → surgical scp แทน + _deploy_remote.ps1 -ExpectMarkers
- [net_guard](reference-net-guard.md) — before/after --allow พิสูจน์รอบอื่นนิ่ง
- [Chrome headless PDF](reference-chrome-headless-pdf.md) — --user-data-dir + poll; ตัดสินไทยด้วย screenshot
- [Google Drive](reference-google-drive-access.md) — SA + Drive API; ค้นไฟล์ query name contains ได้ · [Sheets](reference-google-sheets-access.md) — open_by_key เท่านั้น; 60 reads/min
- [Deploy ผ่าน Tailscale](reference-deploy-via-tailscale.md) — yklog@100.97.150.114; quote ซ้อนพัง→scp .ps1
- [MVP server deploy](reference-mvp-server-deploy.md) · [restart gotcha](reference-mvp-deploy-restart-gotcha.md) — kill by 8010-PID เท่านั้น
- [Branch flips mid-session](reference-branch-switch-during-session.md) — เช็ค branch ก่อน mutation
- [LINE archiver](reference-line-archiver.md) — port 8020 · [DNS](reference-yklogistics-dns.md) — A/MX/SPF ห้ามหาย · [SSH](reference-ssh-to-yk-machine.md)
- [Server no GPU](reference-server-no-gpu-llm.md) · [Window-warm 06/11/16/21](reference-window-warm-routines.md) · [Windows stack ถูกแล้ว](reference-windows-vs-linux-stack-choice.md) · [Auto-resume](reference-auto-resume-system.md)
- [Qwen subagent](reference-qwen-subagent.md) — read-only ฟรี · [Superpowers + 9arm](project-superpowers-9arm-models.md) — ห้ามงานเงิน
- [HOME pwsh](reference-home-pwsh-terminal-setup.md) · [Makcu (ส่วนตัวโอ)](reference-makcu-macro-engine.md) · [YT summarize](reference-yt-summarize.md) · [CC installs](claude-code-multiple-installs.md)
- [🌀 พัดลม MSI GF63](reference-msi-laptop-fan-ec.md) — EC ตรง; ดูรุ่นจาก BaseBoard

## ประวัติ/โดเมน (มิ.ย. และก่อนหน้า)
- [KB ราคาคนขับ](project-kb-driver-calc-price.md) — (override??rev)−kb · [BigC คอลัมน์ E](project-bigc-column-e-customers.md) · [BigC พ.ค.](project-bigc-may-payroll.md) — เดือนมิ.ย.=วิ่งพ.ค.
- [CFO cycle vs calendar](project-cfo-cycle-vs-calendar.md) · [รถร่วมบุญนาม](project-rojruam-bunnam-todo.md) — รอสูตร 13%
- [DHL Oatside มิ.ย.](project-oatside-jun-dhl-checkback.md) — P/R/T/W=เรา Q/S/U/X=DHL
- [LCB daily↔fuel cross-check](project-lcb-daily-fuel-crosscheck.md) · [กติกา](project-lcb-fuel-crosscheck-domain-rules.md) — เติมข้ามไซท์=ปกติ
- **LCB:** [daily sheet](project-daily-lcb-sheet.md) · [mixed](project-lcb-mixed-mode.md) · [idle-days](project-lcb-mixed-idle-days.md) · [Jun reimport](project-lcb-jun-xlsx-reimport.md) · [พ.ค. lock](project-lcb-may-lock-pdf.md) · [slip-reader](project-lcb-slip-reader.md)
- **น้ำมัน:** [exclude-from-driver](project-fuel-exclude-from-driver.md) · [Mao วัดถัง](project-mao-fuel-tank-measure.md) · [handover BACKLOG](project-fuel-handover-measure-backlog.md) · [pump reconcile](project-fuel-pump-reconcile.md)
- **เงินเดือน/บิล:** [Deposit งวด](project-deposit-installment-number.md) · [Deposits overview](project-deposits-overview-page.md) · [pay breakdown](project-driver-pay-breakdown-daily-slip.md) · [bank+print](project-payroll-bank-print.md) · [multi-site onboard](project-multisite-payroll-onboard.md) · [DHL Overflow](project-dhl-overflow-rate.md) · [BigC import](project-bigc-daily-import.md)
- **อื่นๆ:** [CFO drill-down](project-cfo-revenue-drilldown.md) · [Oatside recon](project-oatside-billing-recon.md) · [Oatside UI](project-oatside-report-ui-edits.md) · [UPS alert](project-ups-power-alert.md) · [Daily grid UX](project-daily-grid-edit-ux.md) · [Merge Daily+Grid](project-merge-daily-grid.md)
