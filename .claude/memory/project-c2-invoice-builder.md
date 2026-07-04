---
name: project-c2-invoice-builder
description: C2 ออกใบวางบิล /billing/invoice — engine verified 5 ใบจริง; เหลือ vendor template ลูกค้าที่เหลือ; ไม่เขียน DB
metadata: 
  node_type: memory
  type: project
  originSessionId: 7f48f8d8-b566-4b51-bac0-d33592030d81
---

C2 (3ก.ค.2569 กลางคืน): `/billing/invoice` เติมฟอร์ม xlsx จากสำเนาใบจริง (`app/invoice_templates/`) — **CY+KMMT+CJ** ใช้ได้; `tools/verify_invoice_builder.py` PASS 6 ใบจริงเลขตรงทุกช่อง; **NHL เลื่อน — ไฟล์จริงมี 2 เลย์เอาต์ (WH vs Mitsubishi) ทีมแทรกแถวเอง ต้องถามว่าแบบไหน canonical**

**Why:** ใบวางบิลทุกเจ้า pattern เดียว (ชีทค่าขนส่ง แถวตู้ row16+, ปะหน้า=สูตร) และราคา J = DailyJob.revenue_customer เป๊ะ (CY หลัง A1 ก็ใช่ — revenue=5000 ราคาเก็บจริง kb แยก) ส่วนค่าทดรองจ่าย/ป้าย B,G/BL ของ CY **ไม่มีใน DB** ต้องกรอกในฟอร์ม

**How to apply:**
- เพิ่มลูกค้าใหม่ = runbook ใน docs/INVOICE_BUILDER_SPEC.md (~30 นาที/เจ้า, Sonnet ทำได้) — mapping: CJ→CJIV, JGL→JGIV, KTL→KLIV, KAO→MTIV, NHL→NHIV, WHALE→WHIV
- ระบบ**ไม่เขียน invoice_no กลับเดลี่** (กันเลขชน) — โอต้องเคาะก่อนถึงจะให้เขียน
- verify ใช้ DB สำเนา server จาก C:\Users\guole\YK_BACKUPS_MIRROR (zip S1) — local DB stale
- gotcha ข้อมูล: LCB เดลี่ import ถึง 15/6 เท่านั้น (รอบ 16→15); เจอ invoice_no ขยะ 'KTIV2606-035\t19/6/2026' ใน grid — parse_invoice_no ทนแล้ว; ใบจริงบางใบมีบรรทัดเก็บเพิ่ม (3,000) ที่ไม่อยู่ในเดลี่ + วันที่บรรทุกต่างเดลี่ได้ 1 วัน (ทีมปรับมือ)
- โฟลเดอร์ Drive "ใบวางบิล LCB" id `1kuME7KipmIp_P4NFvbcXlZCXzH2uH6n4` — ลูกค้าครบทุกเจ้า [[project-cy-kb-payout-calculator]] [[project-c1-billing-ready]]
