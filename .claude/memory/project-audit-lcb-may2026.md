---
name: project-audit-lcb-may2026
description: ผลตรวจเงินเดือน LCB พ.ค.2026 (Excel โอ vs ระบบ) — payrun draft ล้าสมัยต้อง recompute; 5 findings; รายงานเต็มที่ docs/AUDIT_LCB_MAY2026.md
metadata: 
  node_type: memory
  type: project
  originSessionId: 96c569e7-9d82-4145-acd4-3fdea000efa2
---

ตรวจ 4 ไฟล์ Excel โอ (หัวลาก/น้ำมัน/วางบิล/สดย่อย) เทียบระบบ app.db รอบ LCB 16เม.ย.–15พ.ค.2026 เมื่อ 15 มิ.ย. 2026 (ยังไม่แก้ data)

**สรุป:** petty+fuel เกือบตรง; daily+payrun มีปัญหา แต่ **ปรับได้ ไม่ต้องลบทำใหม่**

**finding หลัก:**
- payrun draft #1 คำนวณ **ก่อน** reimport งานวิ่ง 3.5 ชม. → ค่าเที่ยว/net ล้าสมัย → **กด re-compute** (engine ถูกอยู่แล้ว)
- กลุ่มเหมาน้ำมัน (lcb_mao 8 คน) gross=0 เพราะ revenue_customer=0 → net ติดลบหลายหมื่น; ต้อง map รายได้เหมาจาก sheet "เหมาน้ำมัน"
- "พิเศษ" ไม่ใช่บั๊ก — engine คิดเป็น other_income (เที่ยว×100) แยกจาก trip_fee
- import script `reimport_lcb_daily.py` (อยู่ใน `Delete/candidates_you_move_here/`) column mapping ไม่ตรง layout ไฟล์วางบิลปัจจุบัน — **ห้ามรันก่อนแก้** (จะลบ data + อ่านคอลัมน์ผิด)

**How to apply:** งานต่อ = re-compute payrun แล้วเทียบ sheet LCB; ทุกข้อกระทบเงิน → branch แยก+dry-run+โชว์ diff รอ "go" + backup app.db ก่อน. รายงานเต็ม `docs/AUDIT_LCB_MAY2026.md`, findings #1-5 ใน `docs/MVP_TEST_FINDINGS.md`. เครื่องมือเทียบ read-only: `tools/audit_lcb_daily_manual_vs_system.py`. เกี่ยว [[project-mvp-test-plan]] [[feedback-test-data-cleanup-safety]]
