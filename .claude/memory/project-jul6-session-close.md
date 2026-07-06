---
name: project-jul6-session-close
description: ปิดเซสชัน 6ก.ค. (วันรองสุดท้าย Fable) — อุด /uploads + viewer เทสต์ + วัด D1 สด + ซ่อม backup ชั้น 3 + ย้ายกล่องไลน์รอคัด /todo; สถานะส่งไม้ Opus 7ก.ค.
metadata: 
  node_type: memory
  type: project
  originSessionId: aed30055-04c8-4590-a662-8674d710dedb
---

**เซสชัน 6 ก.ค. 2026 (10:00-11:15 — deploy เขียวทุกตัว, commit ครบบน branch fix/slip-trip-fee-kb-display + ff main ทันทุกจุดจนถึง a7adf70; เหลือ ff รอบท้าย + ui(todo) ดู CHANGELOG หัวข้อ 2026-07-06):**

1. **ปิดช่องโหว่ /uploads public** (ธง ⚠️ S2 ตัวสุดท้าย) — route `serve_upload` เช็ค session/token; `/check/mechanic` พ่วง `?t=`; ยืนยันบนโปรดักชัน anonymous→403; **ความเชื่อเดิม "แก้แล้วพัง Driver PWA" เป็น false — PWA พรีวิวรูป client-side ไม่โหลด /uploads**; server uploads/ ยังว่าง (0 ไฟล์ — รูป E1 ยังไม่เริ่มเข้า)
2. **S5⑦ viewer ปิดด้วยเทสต์** `test_viewer_rbac.py` (ไม่ต้องมีรหัส viewer บน server อีก); checklist ไตรมาสเหลือค้างโอข้อเดียว = ② ไล่รายชื่อ user (**ทั้งระบบยังมี yk1 บัญชีเดียว ทีมแชร์กัน — ดันโอแยกบัญชีรายคน**)
3. **D1 วัดสด 6ก.ค.** (วิธี: probe read-only import `_daily_row_kind` จาก main จริง รันบน server): LCB จบ; **BIGC เม.ย.293+พ.ค.393 / AYU มิ.ย.410+พ.ค.59 แถวราคาว่าง** — งานทีมกดรับเรทใน /billing/fill-prices ไม่ใช่งานโค้ด
4. **backup ชั้น 3 เคยเงียบหายวันใช้แบต**: `YK_PULL_BACKUP` (เครื่อง Dev = โน้ตบุ๊ก) ติด default DisallowStartIfOnBatteries → แก้แล้ว + StartWhenAvailable; **gotcha ยืน: task ใหม่บนโน้ตบุ๊กต้องตั้ง 2 ค่านี้เสมอ** (จดใน BACKUP_RUNBOOK แล้ว)
5. **ui(todo) โอสั่ง**: กล่อง 📥 จากไลน์รอคัด ย้ายลงท้ายรายการงาน (marker inbox-bottom-jul6)

**ส่งไม้ Opus (7ก.ค. Fable หมด):** ไม่มีงานเงิน/ออกแบบยากค้างแล้ว — ทุกงานที่เหลือติดมือโอ/ทีม/ข้อมูล: A5 ไล่คอลัมน์สลิปกับโอ · D1 ทีมกดรับเรท · F3 รอเดลี่ ก.ค. import แล้ววัด (measure_pod2.py บน server) · AYU ก.ค. รอโอเคาะ กลางรอบ/จบรอบ (เครื่องมือพร้อม [[project-ayu-jul-import-ready]]) · Drive consent §Drive ใน BACKUP_RUNBOOK · ใบเสร็จ/ใบหัก A2 + NHL ฟอร์ม รอตัวอย่าง · **งานปฏิทินถัดไป: ปิดรอบ LCB 15ก.ค. ตาม docs/PAYROLL_CYCLE_CLOSE_RUNBOOK.md** (runbook เขียนไว้ให้โมเดลถัดไปทำเองได้)

**Gotcha ใหม่รอบนี้:** deploy_mvp.sh ไม่ copy `app/oatside/` (ปลอดภัยจาก gotcha config server เป็นตัวจริง) แต่ working tree ยังมี oatside แก้ค้างของอีก session — ห้าม `git add -A` ตามเดิม

related: [[project-master-plan-jul26]] [[project-fable-deadline-and-phase-p]] [[reference-payroll-close-runbook]] [[project-jul3-session-close]]
