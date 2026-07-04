---
name: project-lcb-may-lock-pdf
description: "ปิดเดือน 5 (payrun#1 LCB): ลอกยอดจ่ายจริงจาก PDF ลงระบบ + finalize + guard กัน recompute ทับ. LOCAL DB เสร็จ, ยังไม่ deploy server."
metadata: 
  node_type: memory
  type: project
  originSessionId: cabcef69-ed3b-46a7-8c19-7b9bab9799b2
---

**DONE local 2026-06-27. ปิดเดือน 5 ตามคำสั่งโอ "ลอกตาม PDF เลย จะได้ปิดจบ".**

Ground truth = `Work\Salary\2026\5.May\LCB\LCB ตกหล่นค่าเที่ยวิชาญ.pdf` (อัปเดต 31-05-26, ใหม่กว่า `รวม LCB.pdf` ที่ 375,639). ตารางสรุป + สลิปรายคน 21 คน. รวมจ่ายจริง(net)= **378,939.03**, รวมรายได้= 507,393.

ทำไมต้องลอก: payrun#1 ระบบคำนวณเอง net=333,782 ≠ จ่ายจริง 378,939 (ขาด ~45k). ต่างกระจุกคนเหมา(lcb_mao) — สูตร 60%−น้ำมันถูกทาง (gross/น้ำมันตรงสลิป) แต่ปลายทางเพี้ยนเพราะ sso/ปัดเศษ/เงินเบิก/ขอบรอบ (สลิปหักเบิก 18/5 ที่อยู่นอกรอบ 15/5 ด้วย). โอตัดสิน: ลอกเลขสุดท้ายจาก PDF ทุก field ย่อย ไม่แก้ logic engine.

วิธีทำ (สคริปต์ scratchpad write_may.py): UPDATE payrunitem 21 แถว (match by **payrunitem.id** ไม่ใช่ employee_id — เกือบพลาด, dry-run จับได้). เขียน base/care/trip/special(พิเศษ+รับตู้)/fuel_cost_self(คนเหมา)/sso/deposit/other_deduction(เบิก+อื่น)/gross/net + note `[ปิดเดือน5 lock ตาม PDF จ่ายจริง 31/5/26]`. แล้ว payrun#1 status='finalized'. Backup: `app.db.bak_before_may_lock_pdf_20260627_193502`. ตรวจ 3 ชั้น: รวม net=378,939.03 ✓, gross รายคน=income−fuel mismatch 0 ✓.

CODE CHANGE: `services/payroll.py compute_pay_run()` — เพิ่ม param `force=False`. finalized run จะ**ไม่ถูก recompute ทับแม้ recompute=True** เว้นส่ง force=True (เดิม guard เช็ค `not recompute` ซึ่งไม่กันจริงเพราะ caller ส่ง recompute=True หมด). ทดสอบแล้ว: recompute=True บน finalized → net คงที่ 378,939.

**DEPLOYED server 2026-06-27** (โอสั่ง deploy ทั้ง code+ข้อมูล). ขั้นตอน: push code (guard) ปกติ → backup server DB (`app.db.bak_before_may_lock_push_*`) → stop app (script .ps1-by-path kill main.py procs ตาม [[reference-mvp-deploy-restart-gotcha]]) → scp local app.db ทับ server → restart task. ยืนยัน server: payrun#1 finalized net 378,939.03, daily 1116/max15-6 ไม่หาย, guard code present, port 8010 up, public 200. ปลอดภัยทับได้เพราะเช็คก่อนแล้ว local↔server ตรงกัน (daily 1116, petty 85 เท่ากัน) ต่างแค่ payrun#1.
**SSH หมายเหตุ:** quote ซ้อนใน `python -c`/`powershell -Command` ผ่าน ssh พังตลอด — วิธีที่เวิร์ค = เขียน .py/.ps1 local แล้ว scp ไปรันบน server (เลี่ยง quote นรก). ดู [[project-cfo-cycle-vs-calendar]], [[project-lcb-payroll-may-jun-2026]].
