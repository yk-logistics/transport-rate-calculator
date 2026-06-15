---
name: project-mvp-test-plan
description: แผนทดสอบ MVP end-to-end เริ่ม 2026-06-10 — สถานะ/กติกาอยู่ที่ ProjectYK_System/docs/MVP_TEST_PLAN.md
metadata: 
  node_type: memory
  type: project
  originSessionId: 96546b37-871c-41dc-bf74-362ca98c7ceb
---

โอเริ่มทดสอบ MVP ทั้งสาย (รับงาน→จัดรถ→เดลี่→วางบิล→เงินเดือน→กำไร) ตั้งแต่ 2026-06-10

**Why:** ระบบยังไม่ live โอทดสอบคนเดียวบน DB จริง — ทุกเซสชันต้องรู้ว่าอยู่เฟสไหนโดยไม่ให้โอเล่าซ้ำ

**How to apply:**
- โอพิมพ์ `MVP S<n> ทำต่อ` → อ่าน `ProjectYK_System/docs/MVP_TEST_PLAN.md` (สถานะ+กติกา 8 ข้อ) + `MVP_TEST_FINDINGS.md` แล้วทำต่อทันที
- `จด: ...` = เข้า findings; แก้เป็นชุดในเซสชัน F ยกเว้น blocker
- งานเงินต้องโชว์ตัวเลขเทียบ+แถวกระทบ รอโอพิมพ์ "go"; backup app.db ก่อนแตะข้อมูล
- Ground truth เงินเดือน/บิลจริง LCB พ.ค.: `C:\Users\guole\Desktop\2026.5.28\Desktop\Work\Salary\2026\5.May\LCB\`
- น้ำมันเหมา + กำไรขั้นต้น: ดู [[business-domain-yk]] (`CLAUDE_MEMORY/business_domain.md`)
- B-series (booking→บอร์ดจัดรถ→ร่างเดลี่) = ส่วนหนึ่งของ MVP เริ่มหลัง S1 — สเปคที่ `ProjectYK_System/docs/DISPATCH_BOOKING_SPEC.md`; GPS ไป backlog (รอ API จาก Mobile Innovation/Cartrack)
