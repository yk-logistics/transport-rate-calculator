---
name: project-quote-recalc-stale-fix
description: "บั๊ก /quote กดแก้ไขข้อมูล/คำนวณใหม่แล้วตารางค้างค่าเดิมต้อง F5 — แก้แล้ว 10ก.ค. (dcd1714, deploy แล้ว): บล็อกโรงงานเก่า override ค่าวิซาร์ดใหม่"
metadata: 
  node_type: memory
  type: project
  originSessionId: 474ed162-47d7-4eae-a927-755e923468c6
---

**10 ก.ค. 2026 — โอเจอบั๊กเครื่องคิดเรท `/quote`:** คำนวณครั้งแรกแล้วกด "↺ แก้ไขข้อมูล / คำนวณใหม่"
กลับไปแก้ค่า (ฐาน/ช่วงน้ำมัน) → กดคำนวณ → ตารางค้างของเดิม ต้อง F5 ถึงหาย

**เหตุ:** คำนวณครั้งแรก `initFactoryBlocksFromWizard()` snapshot ค่าฐานเข้า `factoryBlocks[0]`;
กดคำนวณรอบถัดไป `generateResult()` เห็นว่ามีบล็อกแล้ว → `readFactoryBlocksFromEditor()` อ่านค่าเก่า
จาก DOM editor ในหน้าผลลัพธ์ (ที่ซ่อนอยู่) ทับค่าวิซาร์ดใหม่ — มีแค่ราคาน้ำมัน+% ที่ไหลผ่าน;
F5 หายเพราะ reload ล้าง factoryBlocks

**แก้ (dcd1714, deploy server แล้ว — /quote อ่านไฟล์สดทุก request ไม่ต้อง restart):**
1. `generateResult()`: ค่าฐานบล็อกแรกตามวิซาร์ดเสมอ (`factoryBlocks[0].baseRate/baseIdx = w.*`)
2. `backToWizard()`: เติมช่องฐานในวิซาร์ดจากบล็อกแรก (เผื่อแก้จาก editor โรงงานมา — ค่าที่เห็น=ค่าที่ใช้)
- เส้นทางแก้ใน editor หน้าผลลัพธ์ (`onFactoryBlocksChange`) ไม่แตะ — ทำงานเดิม

**Verify:** jsdom harness (node, scratchpad) จำลอง flow จริง — ก่อนแก้ FAIL 2 จุด (ฐานค้าง 18,280
ทั้งที่แก้เป็น 20,000 / แก้ช่วงแล้วช่วงเปลี่ยนแต่ราคาค้าง) หลังแก้ ALL PASS; pytest quote pages 4 passed

**Gotcha ไฟล์คู่:** `app/quote_calc.html` (เสิร์ฟจริง) ↔ `TransportRateCalculator/transport_rate_calculator.html`
ต้อง **byte-identical** เสมอ (แบบเดียวกับ engine Oatside) — แก้แล้ว copy ทับอีกตัว; `/quote` บน server
ติดล็อกอิน (303) เช็คของใหม่ผ่าน curl ตรงๆ ไม่ได้ ให้ grep marker ในไฟล์ server แทน

ดู [[project-b2-quote-save]] · [[project-oatside-jun-dhl-checkback]]
