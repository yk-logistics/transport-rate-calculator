---
name: project-jul-close-prep
description: "เตรียมปิดรอบ ก.ค. 23ก.ค. — LCB run19/AYU run20 draft บน server, import+link+petty LCB ครบ, reconcile 18/18 ตรง; บล็อก: 4 วันอาทิตย์ไม่ลงค่าเที่ยว + คนใหม่ 3+วันชัย inactive + วังน้อยเข้าไม่ได้"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5f2a2d3a-f0bb-4f0f-95a4-63692d8010a8
  modified: 2026-07-23T05:12:11.285Z
---

**23 ก.ค. 2026 — เตรียมปิดรอบ ก.ค. ทั้ง LCB (เลยกำหนด 15/7) + AYU (กำหนด 25/7)** —
รายงานเต็ม: `ProjectYK_System/reports/LCB_AYU_2026-07_CLOSE_PREP_2026-07-23.md`

- **run 19 = LCB 2026-07 draft** (18 คน net 507,667.20 หลังหักน้ำมัน+สดย่อย) ·
  **run 20 = AYU 2026-07 draft** (net 203,011.10 ยังไม่มีสดย่อย/office)
- เดลี่ LCB 659 แถว (source `lcb_jun-jul2026`) + AYU 787 (re-import wipe หลังพิสูจน์ 0 แก้/0 เลขใบ);
  สดย่อย LCB 18 คน 134,931.02 (คอลัมน์ M ชีทสด — มิ.ย. เคยเป็นคอลัมน์ O ไฟล์ทีม)
- เครื่องมือใหม่ใช้ซ้ำได้ทุกรอบ: `tools/lcb_link_drivers.py` (ผูกชื่อเต็ม + น้ำมันตามเดลี่),
  `tools/import_lcb_petty_cycle.py` (parameterized, หา header เอง, ผูกเฉพาะคนใน payrun)
- **gotcha: engine โหมดเหมา (lcb_mao/ayu_mao) เก็บ Σค่าเที่ยวลง `fuel_share_income` ไม่ใช่
  `trip_fee_total`** — reconcile ต้องบวกสองช่อง
- **บล็อกปิด LCB**: ①ทีมยังไม่ลงค่าเที่ยว 4 วันอาทิตย์ (21/6, 28/6, 5/7, 12/7) → คีย์แล้ว
  re-import --wipe-prior (ห้ามแก้ grid ก่อน) ②โอเคาะ: วันชัย emp81 inactive กลับมาวิ่ง 40 แถว
  (ค่าเที่ยว 17,113.80 + สดย่อย 9,430) / คนใหม่ สมหมาย ภูมิสาขา·อนันทร์ แก้วคำ·ภูมิชัย แสนศรีมน
- **บล็อก AYU**: สดย่อยวังน้อย ก.ค. เข้าไม่ได้ (gsheet ไม่แชร์ให้ SA + ไม่มีไฟล์ 7.Jul) →
  ขอโอแชร์เล่มวังน้อยให้ SA อ่าน; office copy จากรูปเงินเดือน; คนไม่ผูก: ไกรวิชญ์/บุญนาม(รถร่วม 13%)/
  ชัยเจริญ/อดิศักดิ์/อุดมชัย; วันปิด re-import สุดท้าย+link ซ้ำ
- ชีท AYU มีแถวคีย์ล่วงหน้าถึง 31/7 (นอกหน้าต่างถูกตัดอัตโนมัติ) — ปกติ

**รอบสอง 23ก.ค. (โอสั่ง "ทำอะไรได้อีกทำไปก่อน"):** เพิ่ม `tools/lcb_reconcile_run.py`
(reconcile สองทางถาวร, exit 1 ถ้าไม่ตรง) + runbook อัปเดต gotcha/เครื่องมือใหม่ ·
RM History sync แล้ว (ชีทสด 3 เล่มมีบิลใหม่แค่ 1 ใบ — ระบบซ่อมตามทันอยู่แล้ว; DB ถึง 5/7
เพราะทีมไม่ได้คีย์เพิ่ม ไม่ใช่ระบบค้าง) · เก็บ commit ค้างเซสชันก่อน (wonder B1/B2 + memory 18 ไฟล์ +
operator profile CLAUDE.md) + gitignore `Pictures/` (รูปโอ 349MB) · ปรีชา AYU ธง absent 22 วัน =
ไม่กระทบเงิน (base_salary=0, ayu_trip) แต่เขาหายจากชีทหลัง 3/7 — ถามโอ/ทีมว่าลาออกไหม ·
/todo inbox มีงานทีมค้าง 15 รายการตั้งแต่ 13ก.ค. (เบิกยาง/แจ้งซ่อม/ลาป่วย) — ทีมยังไม่เข้ามาใช้ ·
LCB ก.ค. ไม่มีแถว "จ่ายคนขับแต่ราคาลูกค้าว่าง" (พร้อมวางบิล); DHL Overflow 57 แถว rev=0 = กติกาค่าเสียเวลารอโอ ·
SA เห็นไฟล์ใบวางบิลทีม (KTIV/NHIV/... .xlsx) อัปเดตรายวันใน Drive — ยังไม่ sync เข้าทะเบียน v52 (รอโอตัดสิน)

related: [[reference-payroll-close-runbook]] [[project-lcb-jul-preclose-audit]] [[project-jun-close-3sites]]
