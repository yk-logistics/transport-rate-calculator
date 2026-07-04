---
name: project-jul3-session-close
description: ปิดเซสชันมาราธอน 2-3 ก.ค. (โอนอน ตี 3 ครึ่ง) — สรุปของที่ deploy + คำถามค้างโอ 4 ข้อ + งานถัดไปตามคิว Fable
metadata: 
  node_type: memory
  type: project
  originSessionId: e43bba19-d298-4881-8117-b08646b56d9b
---

**เซสชัน 2 ก.ค. 10:00 → 3 ก.ค. 04:00 (branch fix/slip-trip-fee-kb-display — ยังไม่ merge main; ทุกอย่าง deploy แบบ surgical แล้ว):**

**Deploy จริงครบ (ตามลำดับ):** สลิป KB dispatch pay_mode / P&L หัก KB / ZIP timestamp / /kb-payout 4 เจ้า+ติ๊กรับ+จับคู่เลือกเจ้า / /finance/receivables จัดกลุ่มลูกค้า ปี 2026+ อ่าน Drive โฟลเดอร์ลิงก์ / **เงิน: ลง KB CY 23 แถว (กติกาสุดท้าย: คนขับจากราคาคีย์ kb=5000−คีย์, ถอน +840 แล้ว) + finalize 3 รอบ (LCB 286,871.37 / AYU 263,793.34 / BIGC 132,031.03)** / /admin/plan (แผน+progress) / /todo สมุดโน้ต (v33) / /quote เครื่องคิดราคา + /oatside/report (เสิร์ฟไฟล์เดิมตรง) / /admin/server-health (G1)

**เอกสารแกน (โมเดลไหนก็อ่านต่อได้):** "แพลน MVP" = docs/MASTER_PLAN_2026-07.md + docs/MVP_TASK_SPECS.md (สเปคทุกงาน+กติกา §0 รวมกฎห้ามออกนอกแบบ §0.11) + docs/PLAN_STATUS.json (สถานะ — อัปเดต+scp ขึ้น YK_MVP/docs/ ทุกครั้ง)

**โอตอบแล้ว (3ก.ค. ~04:00 ก่อนนอน):**
1. เลขบัญชี: **โอจะแก้เองถ้าระบบให้แก้ได้** → A5 ต้องมีแก้บัญชีง่ายๆ จากหน้าโอนเงิน (มี /employees/{id}/edit อยู่แล้ว — เพิ่มทางลัด)
2.-3. ใบเสร็จตัวอย่าง + Editor Drive: **จดไว้ถามอีกที** (ยังค้าง)
4. **A3 เปลี่ยนดีไซน์: ติ๊กรับเงิน "ในระบบ" ไม่แตะ Excel** → ตาราง ArSettle (แบบ KbSettle) received = สีในชีท OR ติ๊กในระบบ; ไม่ sync กลับชีท ไม่ต้องขอ Editor
5. **Oatside: สั่งทำเลยทั้ง C3+C5 (แก้เงื่อนไขเองทั้งหมด ไม่พึ่ง AI)** + **ลุยแพลน MVP ต่อได้ทุกอย่างไม่ต้องรออนุมัติ**

**✅ C3+C5 DONE 3ก.ค. 05:00 (ทำต่อหลังโอนอน):** /oatside อัปโหลด GPS→คำนวณ→รายงาน+Excel (engine vendored byte-identical, subprocess, verified server จริง: 152 เที่ยว checksum 1,485,120 ตรงเดิมเป๊ะ) + /oatside/settings แก้เงื่อนไขเองครบทุกหมวด+โหมด JSON ดิบ+backup 20 ชุด; รายงานบน server = build สดจากไฟล์ มิ.ย.; runbook docs/OATSIDE_MVP_RUNBOOK.md; **GOTCHA: config บน server เป็นตัวจริงหลังโอแก้ผ่านเว็บ — ห้าม scp ทับ**; + G1 หน้าสุขภาพเครื่อง DONE ก่อนหน้า

**🟢 มอบอำนาจเต็ม (โอ 3ก.ค. ~05:10 — คำสั่งยืน):** "แพลน MVP ทำได้ทุกอันเลย ถ้าเสร็จ 100% ได้ก็ทำไป อันไหนต้องถามค่อยถามทีหลัง ทำไปก่อนแล้วค่อยแก้ คิดแทนฉันได้หมด" → ทุกเซสชันลุยตามคิวแพลนได้เลยไม่ต้องรออนุมัติ (ยกเว้นกฎเงิน/ทำลายล้าง ยังยึด CLAUDE.md); ตัดสินใจแทนโอแบบ "ทำก่อน-แก้ทีหลัง" + จดทุกข้อสมมติไว้ให้โอรีวิว

**✅ A3 DONE 3ก.ค. 05:40:** ติ๊กรับเงิน AR ในระบบ (ArSettle v34, received=สีชีท OR ติ๊ก, ปุ่มต่อแถว+ยกเลิก, จดคนติ๊ก; verified table บน server) — ตามโอเคาะ "แก้ในระบบ ไม่ใช่ Excel"

**✅ เพิ่มรอบเช้า 3ก.ค. (05:45-06:30 หลัง "ทำต่อ"):**
- A5-ส่วนแรก: หน้า /payroll/{id}/accounts บัญชีโอนเงิน (เลขใหญ่คลิกก็อป, แก้ inline ลง Employee ถาวร, กลุ่มตามธนาคาร, net>0, ปุ่มจากหน้ารอบ) — ส่วนสลิป/ลดปุ่มยังรอ session สลิปเก่า
- F1: /line ค้นแชททุกกลุ่ม+เปิดรูปเก่า+กลุ่มเงียบท้ายตาราง (read-only line_archive.db, verified จริง 44 กลุ่ม; เมนู ปฏิบัติการ→💬; สิทธิ์ office/บัญชี ดูได้)
- GOTCHA: services ห้ามอ่าน env ตอน import (เทสต์ monkeypatch ไม่ติด) — อ่านสดใน function

**คิวงานถัดไป (เซสชันหน้า — มอบอำนาจเต็มแล้ว):** B4 ปฏิทินรถ (สเปคเต็มใน MVP_TASK_SPECS — สำรวจ DispatchPlan/LeaveRecord/Maint ก่อน) → B2 เซฟใบเสนอราคา (ศึกษา JS เครื่องคิดก่อน inject) → C1 เช็คครบก่อนวางบิล → S1 backup (ชั้น Drive รอ Editor; ชั้นอื่นเริ่มได้) → F2 กล่องงานเข้า; **ค้างถามโอ: ตัวอย่างใบเสร็จ/ใบหัก (A2) + Editor Drive (S1)**

**GOTCHA ใหม่คืนนี้:** รอบ finalized ห้าม recompute (สดย่อย deducted แล้ว engine sum กรอง pending → recompute = สดย่อยหาย; แก้ item ด้วยเลขตรงๆ แทน) / finalize ปกติติด gate drift/policy — ยอดเบิกล่วงหน้า 22/6, 29/6 คือของตั้งใจหักรอบนี้ / แก้ deploy หลายไฟล์: probe ทุกไฟล์ก่อนทับเสมอ / oatside_report ห้าม scp -r ซ้ำ (จะซ้อน dir — ลบก่อนหรือ scp เนื้อใน)

related: [[project-master-plan-jul26]] [[project-fable-deadline-and-phase-p]] [[project-lcb-cy-kb-fulls]] [[project-jun-close-3sites]]
