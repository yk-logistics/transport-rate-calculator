---
name: project-jul4-night-run
description: คืน 3→4 ก.ค. Fable รันยาว 13 งาน MVP + deploy v40 แล้ว — สิ่งที่รอโอเคาะ/วัดต่อ
metadata: 
  node_type: memory
  type: project
  originSessionId: 7f48f8d8-b566-4b51-bac0-d33592030d81
---

คืน 3→4 ก.ค. 2569 (โอสั่ง "ทำทั้งคืน ตัดสินใจแทนได้"): ปิด 15 งานบน branch `fix/slip-trip-fee-kb-display` + **deploy server 3 รอบ (schema v36→v41, verify ผ่านทุกรอบ, 8020 ไม่กระทบ)** — เทสต์ทั้งชุด 382 ตัวเขียว; F3 POD /line/pod + /billing/evidence ZIP (v41 JobMedia); **C2 ครบ 9/10 ลูกค้าประจำ** (verified 12 ใบจริง; PX19/Nippon ใบแรกเทียบมือ; NHL รอทีมเคาะเลย์เอาต์); **F4 recon: กลุ่มปั๊มมีแต่รูป ไม่มี xlsx — ต้อง OCR สลิป รอโอเคาะ (จดในสเปคแล้ว)**

**เสร็จ:** B1.1 (nav /quote inject), C2 ใบวางบิล /billing/invoice (CY+KMMT+CJ verified 6 ใบจริงเลขตรง; NHL เลื่อน—ไฟล์ 2 เลย์เอาต์), P3 คลิกขวา YKCtx (3 ที่แรก), P2 audit กลาง /admin/audit + ประวัติช่องใน grid, D2 เงินหมุน 8 สัปดาห์ /finance/cashflow + /finance/debts, D3 กำไรสุทธิ/คัน + sparkline, P1 สิทธิ์รายชิ้นส่วน /admin/permissions (4 จุดแรก + ตัด KB/เงินจาก API payload), F5 /line/digest, F2 /line/inbox (โค้ดเสร็จ), S2 รายงาน SECURITY_S2_APP_AUDIT.md, S4 SECURITY_TEAM_ONE_PAGER.md, S5 SECURITY_QUARTERLY_CHECKLIST.md

**Why (การตัดสินใจแทนที่ทำไป):**
- C2 ไม่เขียน invoice_no กลับเดลี่ (กันเลขชน), template = สำเนาไฟล์จริง
- D2 ข้อสมมติวันจ่ายเงินเดือน BIGC=5/LCB=20/AYU=30 (`PAYROLL_PAY_DAY` ใน finance.py)
- deploy แบบ surgical scp — **พิสูจน์แล้วว่าสลิป template บน server ≠ local (งาน session อื่นยังไม่จบ) ห้ามใช้ deploy_mvp.sh จนกว่าเขา commit/deploy**

**รอบเช้า 4ก.ค. (06:44–07:45) เพิ่มอีก 5:** แก้เมนูหลุดขอบจอมือถือ (clamp ทุก dropdown), **F2 วัดกับข้อความจริง 1,256 รายการ + จูน** (ตัดโพสต์แจกงานตัวเอง หัว-หาง, เพิ่มคำจอง/1x40/รับงานได้ — จับ 71 อ่านไล่แล้ว ~90% งานจริง) + เดา mapping กลุ่มจากชื่อ, A5 จัดปุ่ม payroll เหลือ 3 ปุ่มใหญ่ (สลิปคนขับ/ชุดบอส/ZIP + เพิ่มเติม▾), **P5 เมนู 5 หมวดตาม flow** (รับงาน/หน้างาน/เงิน/ผู้บริหาร/เครื่องมือ — URL เดิมครบ), **หน้าแรก / = การ์ดงานวันนี้** (home_dashboard.html + cache ไลน์ 5 นาที) — deploy ครบทุกตัวแล้ว เทสต์ 385 เขียว

**รอบ 2 เช้า (07:45–08:45) เพิ่มอีก 2 + ปิดแพลนที่ 31/38 (82%):** E2 /fuel/anomaly (เติมถี่/เกินถัง/วันไม่มีงาน — v42 Vehicle.tank_liters กรอกที่ /vehicles) + **E1 Driver PWA 3 หน้า** (/driver/checkin จุด รับตู้-ถึงงาน-คืนตู้ + /driver/container รูป 4 ด้าน ไม่ครบ=flagged + /driver/done — ผูก daily_job_id จาก dropdown งานวันนี้, review ที่ /admin/submissions เดิม) — deploy แล้ว server v42, เทสต์ 395 เขียว; **7 งานที่เหลือติดเงื่อนไขภายนอกทั้งหมด** (A2 ตัวอย่างเอกสาร / A5 สลิป+โอ / D1 กับโอ / F3-F4 วัดจริง+OCR / G2 เมื่อถึงเวลา / S3 token กับโอ)

**รอบ 3 สาย (09:00–10:00) — โอปลดบล็อค A2 + มอบอำนาจเต็ม:** **A2 เสร็จ** — ใบเสร็จ+ใบหัก 50ทวิ ฟอร์มมาตรฐาน `/kb-payout/receipt?invs=` (เลขเอกสาร DocIssue idempotent; เคสสเปค 1,713→51.39→1,541.70 ในเทสต์) + **🎨 Doc Designer `/admin/doc-designer`** (ลาก/ขยาย/ดับเบิลคลิกแก้ข้อความ/เพิ่มชิ้น บน A4 หน่วย mm → DocTemplate v43 override default ในโค้ด, reset ได้, แก้→AuditLog — **ฟอร์มใหม่อนาคต = เพิ่ม key ใน DEFAULT_TEMPLATES ได้ designer ฟรี**); **D1 เครื่องมือ ⚡ /billing/fill-prices** (เรท RateCard เสนอ+กดรับต่อแถว pattern B3) — deploy หมดแล้ว v43, เทสต์ 403 ตัวเขียว; แพลน 33/38 เหลือ F4/G2/S3 + งานข้อมูล/วัดจริง

**รอบ 4 (10:00–10:33):** คลิกขวา grid "📷 ดูรูปงานนี้" (รวมรูปไลน์ JobMedia + มือถือคนขับ DriverSubmission — ปิด loop E1/F3 ตามสเปค P3), แบนเนอร์แดงจำนวนธงผิดปกติบน /fuel, **P5.1 ลากเรียงหมวดเมนูเอง** (เครื่องมือ→จัดเรียงเมนูเอง, localStorage ต่อเครื่อง) — P5 ครบชุดแล้ว; deploy ครบ

**รอบ 5 นอกแพลน (10:35–12:00 โอสั่ง "ไม่ต้องตามแพลน ลุยยาว"):** 🔍 **Global Search /search** (ช่องค้นบน nav ทุกหน้า — เดลี่ 8 ฟิลด์/พนักงาน/รถ/ลูกค้า/น้ำมัน/ใบเสนอ/แชทไลน์ กรอง section ตามสิทธิ์; gotcha: Jinja `sec.items` = dict.items method ต้องใช้ `sec['items']`), การ์ดหน้าแรก 💵 AR เลยกำหนด/ครบ 7 วัน (Drive cache 10 นาที) + ⛽🚩 น้ำมัน 7 วัน, ⬇️ CSV โอนชุดธนาคาร (/payroll/{id}/accounts.csv BOM), 🧹 เลขใบสกปรก normalize ตอนเซฟ + /admin/data-clean, ctx ประวัติแก้บัญชี — deploy ครบ เทสต์ 414 เขียว

**รอบ 6 ops (12:0x–13:35):** พบว่า server **ไม่มี log เลย** (SYSTEM task stdout หาย — 500 หายเงียบ) → เพิ่ม RotatingFileHandler `app/logs/app.log` + exception handler จับ traceback ทุก 500 + กล่อง "🐞 ข้อผิดพลาดล่าสุด" บน /admin/server-health; และ **8010 ไม่มีใครเฝ้า** → watchdog `YK_MVP_HEALTHPOLL` (ทุก 5 นาที: probe local+public, ล่มใหม่→สตาร์ทกลับอัตโนมัติ 1 ครั้ง/รอบล่ม, alert Discord #yk-mvp-alerts เฉพาะเปลี่ยนสถานะ — ติดตั้ง+ยิงทดสอบจริงแล้ว); **gotcha: Cloudflare+Discord 403 UA 'Python-urllib' ต้องตั้ง User-Agent เอง**; เทสต์ 415 เขียว

**รอบ 7 ปิดท้าย (13:4x–14:0x):** โอรายงานบั๊กจริง — **/todo แนบรูปไม่ขึ้น**: ปุ่มนับรูป `innerText` ทับ parent ลบ `<input type=file>` ตัวเอง → รูปไม่เคยถูกส่ง (แก้: อัปเดตเฉพาะ span + เพิ่มบีบรูปเป็น JPG ฝั่งเครื่องแก้ HEIC iPhone + เทสต์เต็มสาย); จากนั้น **audit ทั้งระบบหาบั๊กตระกูลเดียวกัน**: กวาด innerText/innerHTML ทุก template + file-input ทุกฟอร์มต้องมี enctype (HTMX = hx-encoding) + form คร่อม tr — **ไม่พบเพิ่ม** (check_mechanic label เป็น sibling ปลอดภัย, check_driver #slots เป็นพรีวิวแยกจาก input, import_hub ใช้ hx-encoding ถูก); บทเรียน: **ตัวนับ/พรีวิวห้ามเขียนทับ element ที่หุ้ม input — ให้ชี้ span แยกเสมอ**

**How to apply (รอโอ/งานต่อ):**
- โอเคาะ: วันจ่ายเงินเดือนจริง (D2) + กรอกหนี้ /finance/debts + mark กลุ่มลูกค้า /line/inbox แล้ววัด F2 ≥80% กับข้อความจริง + อ่าน SECURITY_TEAM_ONE_PAGER แจกทีม
- ~~/uploads เปิด public (S2 พบ)~~ ปิดแล้ว 6ก.ค. (3bd3fce deploy เขียว — PWA คนขับไม่โหลด /uploads จริง ที่กลัวไม่เกิด; ช่างยาง magic link ใช้ ?t=)
- C2 เพิ่มลูกค้า: runbook ใน INVOICE_BUILDER_SPEC.md (~30 นาที/เจ้า Sonnet ทำได้); NHL ต้องถามทีมว่าฟอร์มไหน canonical
- งานที่เหลือในแพลน: A2/A5/D1/P5 (ต้องโอ), F3/F4 (ต้องดู media จริงบน server), G2 (ไฟล์บน server), S3 (rotate token — ทำตอนโอตื่น)
[[project-c2-invoice-builder]] [[project-master-plan-jul26]] [[reference-mvp-server-deploy]]
