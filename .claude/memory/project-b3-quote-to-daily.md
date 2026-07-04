---
name: project-b3-quote-to-daily
description: B3 ราคาไหลเข้าเดลี่/บิล DONE 3ก.ค. — ปุ่ม 💡 ในหน้าเดลี่ + เตือนราคา≠ใบเสนอใน /billing; matcher เข้ม ลูกค้า+ปลายทางต้องตรงทั้งคู่ กดรับถึงเขียน
metadata: 
  node_type: memory
  type: project
  originSessionId: 742a8c2c-bba6-475f-bb99-ce05aba9b6ba
---

**B3 DONE 3 ก.ค. 2026 (งานเงิน ทำโดย Fable ตามกฎ; code-only ไม่แตะ DB/engine):**
- ปุ่ม "💡 ราคาจากใบเสนอ" บนหน้า /daily grid → GET `/api/daily-jobs/quote-suggest` (ตาม filter site+ช่วงวันปัจจุบัน) โชว์แถวราคาว่างที่ match ใบเสนอ status=agreed → คนคีย์กด "รับ" ต่อแถว (หรือรับทั้งหมด) → POST `/api/daily-jobs/apply-quote` เขียน revenue_customer + แถว DailyJobAudit action=`quote_apply`
- **กติกาเงิน:** เขียนเฉพาะแถวราคาว่าง (revenue<=0) — มีราคาแล้ว = 409 ไม่ทับ; server ตรวจ match ซ้ำเอง ไม่เชื่อ payload; ไม่แตะ trip_fee_driver/engine (mao จ่ายจาก trip_fee_driver อยู่แล้ว, รอบ finalized ไม่ recompute)
- **Matcher (`_quote_price_match` ใน main.py — เข้มไว้ก่อน):** ต้องตรง**ทั้งคู่**: ชื่อลูกค้าใบเสนอ = customer_name_raw/status_code/ชื่อ master (normalize เท่ากันเป๊ะ) **และ** ชื่องาน/โรงงานใบเสนอเป็น substring ของปลายทางเดลี่ (หรือกลับกัน); ใบต้อง agreed+price_agreed ไม่ใช่ draft
- /billing แถบพร้อมวางบิล เพิ่มเกณฑ์ที่ 4: "ราคาไม่ตรงใบเสนอ" (ลงไว้ X แต่ตกลง Y ลิงก์ไปใบเสนอ) — ครบ 4 เกณฑ์ตามสเปค C1+B3
- สิทธิ์: /api/daily-jobs/* อยู่ menu daily → office (คนคีย์) กดรับได้
- เทสต์ 5 ตัว tests/test_quote_price_flow.py (match/apply+audit/ไม่ทับ+mismatch 409/billing เตือน/draft ไม่เสนอ)
- **ยังไม่มีผลกับข้อมูลจริงจนกว่าโอจะมีใบเสนอ status=ตกลงแล้ว ใน /quote/list** (ตาราง Quotation บน server ยังว่าง) — flow จริง: เซฟจากเครื่องคิด → เปิดใบ → ตั้งสถานะตกลง+ราคาตกลง → ปุ่ม 💡 ในเดลี่จะเริ่มเห็น

related: [[project-b2-quote-save]] [[project-c1-billing-ready]] [[project-master-plan-jul26]]
