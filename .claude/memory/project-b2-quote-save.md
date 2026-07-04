---
name: project-b2-quote-save
description: B2 เซฟใบเสนอราคา DONE+deployed 3ก.ค. — /quote/sync พูดโปรโตคอล Drive-sync เดิมของเครื่องคิด (ไม่แก้ไฟล์ 168KB) + /quote/list + Quotation v35
metadata: 
  node_type: memory
  type: project
  originSessionId: 742a8c2c-bba6-475f-bb99-ce05aba9b6ba
---

**B2 DONE+deployed 3 ก.ค. 2026 (commit 0f7a066, surgical scp 5 ไฟล์, verified: SchemaInfo v35 + ตาราง quotation/quotationaudit บน server):**

**ดีไซน์หลัก (ต่างสเปคเดิมแต่ดีกว่า):** ไม่แตะไฟล์เครื่องคิด transport_rate_calculator.html เลย — ไฟล์มีปุ่ม "บันทึกงาน" + ระบบ Sync to Drive (URL ตั้งได้ผ่าน localStorage `yk_drive_sync_settings_v1`) อยู่แล้ว → MVP ทำ `/quote/sync` พูดโปรโตคอลเดียวกัน (POST text/plain `{action:'save',payload:{records}}` / GET `?action=load` คืน `{records}`) + route /quote inject `<script id="yk-quote-sync-bootstrap">` ต่อท้ายตอนเสิร์ฟ ตั้งค่าครั้งแรกอัตโนมัติ (url=/quote/sync, autoSync+autoLoad on) — auth ใช้ session cookie (same-origin fetch), field secret ไม่ใช้

**โครง:** Quotation v35 (record_id unique จากเครื่องคิด 'job_...', raw_json=record+snapshot ทั้งก้อน→โหลดกลับค่าเดิมครบ, ฟิลด์ถอดไว้ค้น: customer/factory/km_round/toll/price_offered (customerPrice>0 หรือ ราคาเป้า margin ขั้นต่ำ)/location_url/origin_site) + QuotationAudit insert-only; ลบในเครื่องคิด→archived (ไม่ลบจริง ไม่โผล่ load); แก้ในระบบ: /quote/{id} สถานะ+price_agreed

**GOTCHA:** (1) sync save = full-state replace ฝั่งเครื่องคิด — record หายต้อง archive ไม่ใช่ลบ, sync กลับมาอีก→คืน draft (2) init เครื่องคิดรันตอน parse — script inject ท้าย body ต้องเรียก loadDriveSettings()+loadFromDrive(true) เองรอบแรก (3) PS inline `count(*)` ผ่าน ssh พัง — เช็ค DB ด้วย .py scp ขึ้นไปรันเสมอ

verified: pytest 8 ตัว (round-trip เกณฑ์ผ่าน B2 + audit 2 แถว) + suite เต็ม 322 pass; **ยังไม่ได้ลองกดจริงในเบราว์เซอร์ — ให้โอเปิด /quote กดบันทึกงาน 1 ครั้งแล้วดู /quote/list**; handoff เต็มใน MVP_TASK_SPECS §B2

related: [[project-master-plan-jul26]] [[project-b4-fleet-calendar]]
