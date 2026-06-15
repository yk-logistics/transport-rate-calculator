---
name: feedback-test-data-cleanup-safety
description: ลบ test row ที่ POST เข้า DB จริง ต้องลบด้วย id ที่ insert คืนมาเท่านั้น — ห้ามลบด้วย filter (work_date/destination) เพราะชนข้อมูลจริง
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 1d19758a-9d43-46dd-b0a9-91adaaa63ea2
---

ตอน debug หน้า /daily/new ผม POST test row เข้า app.db จริง แล้ว cleanup ด้วย
`DELETE FROM dailyjob WHERE work_date='2026-05-03'` → **ลบข้อมูลจริงของโอไป 3 แถว** (id 296/297/298)
เพราะวันนั้นมีงานจริงอยู่แล้ว ต้องกู้จาก app.db.backup_20260610

**Why:** app.db = DB จริงที่โอทดสอบ MVP (ไม่มี DB แยก — ดู [[project-mvp-test-plan]]).
filter อย่าง work_date/site/destination ชนกับข้อมูลจริงได้เสมอ. กฎเงิน/ข้อมูลของ repo ห้ามแตะข้อมูลโดยไม่ระวัง.

**How to apply:**
- POST test เข้า DB จริง → เก็บ `id` ที่ API คืนมา → ลบด้วย `WHERE id IN (<ids ที่ได้>)` เท่านั้น
- **ก่อนแตะ app.db ทุกครั้ง backup ก่อน** (กติกา MVP ข้อ 8) — มี backup ถึงกู้ได้รอบนี้
- ดียิ่งกว่า: ทดสอบ endpoint แบบไม่ commit จริง หรือใช้ค่าที่ระบุชัดว่าเป็น test (destination=TEST_DELETE_ME) **แล้วลบด้วย id** ไม่ใช่ลบด้วยค่านั้น
- backup ที่กู้ได้: `ProjectYK_System/app/app.db.backup_20260610` (508 daily rows ตรงกับสถานะ MVP)
