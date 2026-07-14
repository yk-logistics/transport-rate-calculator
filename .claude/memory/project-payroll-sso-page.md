---
name: project-payroll-sso-page
description: "หน้า สปส. /payroll/sso ให้หมิว (14ก.ค.) — รวมรอบปิดแล้วต่องวดจ่ายเดือน (BIGC เลื่อน 1) + toggle ss_exempt มีผลรอบหน้าเท่านั้น + ตารางรอโอนคืน; ค้าง: วิธีบันทึกการโอนคืน รอโอเคาะ"
metadata: 
  node_type: memory
  type: project
  originSessionId: fd0894dd-f24f-402b-bcc2-26a58006d9bf
---

หน้า `/payroll/sso` (14 ก.ค. 2026, โอสั่งให้หมิวใช้ยื่นเงินสมทบ):

- งวดจ่ายเดือน M = LCB tag M + AYU tag M + **BIGC tag M-1** (`_sso_pay_month` ใน main.py —
  กติกาเดียวกับ [[project-cfo-compare-bigc-anchor-shift]]); เอาเฉพาะรอบ finalized/paid,
  draft โชว์เป็นป้าย "ยังไม่ปิด"
- ตัวเลข = PayRunItem.gross_total / .social_security ตรง ๆ (ตรงสลิป) — read-only ต่อรอบเดิม
- ปุ่มตั้ง "ไม่หัก" = merge `custom_terms.ss_exempt` (กลไกใน services/payroll.py มีอยู่ก่อนแล้ว
  บรรทัด ~1236) + audit_log; **รอบ finalize ไม่เปลี่ยน** (กฎเหล็กข้อ 2); custom_terms
  ที่เป็นข้อความไม่ใช่ JSON → toggle ถูกปฏิเสธ 400 (กันทับข้อตกลงเดิม — มีเทสต์)
- ตาราง "รอโอนคืน" = คน ss_exempt ปัจจุบัน × Σ สปส. ที่เคยหักในรอบปิดแล้ว (ทุกงวด)

**ค้างรอโอ:** หมิวโอนคืนแล้ว จะบันทึกในระบบยังไง (ตอนนี้หน้าโชว์ยอดเฉย ๆ ไม่หักลบ/ไม่ติ๊กจบ) —
ถ้าโอนคืนบ่อยควรมีปุ่ม "คืนแล้ว" + log; อย่าทำเองก่อนโอเคาะ

ยอดอ้างอิงงวด 2026-06 บน server (นับจาก DB 14ก.ค.): สปส.รวม 19,994
(LCB 6,216 / AYU 10,266 / BIGC-พ.ค. 3,512); เทสต์: tests/test_payroll_sso.py
