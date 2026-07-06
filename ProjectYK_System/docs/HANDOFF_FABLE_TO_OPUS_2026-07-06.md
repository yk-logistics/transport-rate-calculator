# [HANDOFF Project YK] Fable → Opus (เขียน 6 ก.ค. 2026 — Fable หมดอายุ 7/7)

> ผู้รับ: Opus (หรือโมเดลใหญ่สุดที่โอมี) — เปิดเซสชันใน repo `Project YK` แล้วอ่านตามลำดับ
> CLAUDE.md บังคับก่อนเสมอ; เอกสารนี้เป็นแค่ตัวเร่ง ไม่แทนที่ไฟล์ในระบบ
> **อ่านคู่กัน: [`FABLE_MINDSET_FOR_OPUS.md`](FABLE_MINDSET_FOR_OPUS.md)** — วิธีคิด/วินัยการทำงานที่โอขอให้ Fable กลั่นทิ้งไว้ (ไฟล์นี้=สถานะงาน, ไฟล์นั้น=จังหวะคิด)

## สถานะ ณ ปิดเซสชัน 6 ก.ค. ~11:20

- **แพลน MVP: 35/38 done** — ดู `ProjectYK_System/docs/PLAN_STATUS.json` (sync กับ server แล้ว, หน้า /admin/plan โชว์ตรง)
- **ไม่มีงานเงิน/ออกแบบยากค้างสำหรับโมเดลใหญ่แล้ว** — ทุกงานที่เหลือติดเงื่อนไขภายนอก (มือโอ/ทีม/ข้อมูล ก.ค.)
- Branch: `fix/slip-trip-fee-kb-display` — commit ล่าสุดของเซสชันนี้ต้อง ff เข้า `main` (เช็ค `git log main..HEAD` ถ้ามีค้างให้ `git merge --ff-only`)
- ทุก deploy ของเซสชันนี้เขียวหมด ยืนยันบนโปรดักชันแล้ว
- งานเซสชันนี้ทั้งหมด: `ProjectYK_System/CHANGELOG_MASTER.md` หัวข้อ `## 2026-07-06` (อ่าน 3 หัวข้อแรกพอ ตามนโยบาย)

## งานที่รอ trigger ภายนอก (อย่าไปทำเอง — รอสัญญาณ)

| งาน | รออะไร | เมื่อได้สัญญาณ ทำตาม |
|------|--------|---------------------|
| ปิดรอบ LCB งวด 16มิ.ย.→15ก.ค. | ถึงวันที่ ~15 ก.ค. + เดลี่ครบ | `docs/PAYROLL_CYCLE_CLOSE_RUNBOOK.md` (เขียนไว้ให้ทำเองได้ทั้งวงจร — **งานเงิน: โมเดลใหญ่เท่านั้น ห้าม delegate**) |
| AYU ก.ค. import | โอเคาะ กลางรอบ vs จบรอบ 25ก.ค. | memory `project-ayu-jul-import-ready` (preflight รันแล้ว 231 งานไม่มี dupe) |
| F3 วัด ≥90% | เดลี่ ก.ค. import เสร็จ | `measure_pod2.py` บน server (memory `project-f3-pod-measured-tuned`) |
| A5 ไล่คอลัมน์สลิป | โอนั่งไล่กับ AI รอบเดียว | ห้ามเดาเอง — เปลี่ยน display ต้องเทียบ 3 surface (memory `project-slip-surfaces-consistency`) |
| A2 ใบเสร็จ/ใบหัก + NHL invoice | โอส่งตัวอย่าง / ทีมตอบฟอร์ม canonical | `docs/INVOICE_BUILDER_SPEC.md` (runbook เพิ่มลูกค้า ~30 นาที Sonnet ทำได้) |
| Drive backup ชั้นสุดท้าย | โอกดยินยอม OAuth 5 นาที | `docs/BACKUP_RUNBOOK.md` §Drive — consent ต้องสถานะ PUBLISH ไม่งั้น token ตาย 7 วัน |
| D1 เติมราคา BIGC/AYU | ทีมกดรับเรทเอง (ไม่ใช่งานโค้ด) | ตัวเลขสด 6ก.ค. อยู่ใน PLAN_STATUS D1 |

## กติกาสำคัญที่สุดสำหรับ Opus (ฉบับย่อ — ตัวเต็มใน CLAUDE.md + memory)

1. **งานเงิน (payroll/billing/แก้ DB) ทำเองเสมอ ห้าม delegate; ห้ามเดา ไซท์/รอบ/ชื่อคล้าย**
2. **รอบ finalized ห้าม recompute** (สดย่อยหาย — แก้ item ตรงๆ แทน)
3. Deploy: `bash ProjectYK_System/tools/deploy_mvp.sh --markers "<ascii>"` — self-verify ในตัว; **ห้าม git add -A**; oatside config บน server เป็นตัวจริงห้ามทับ
4. มอบอำนาจเต็มจากโอยังมีผล (memory `project-jul3-session-close`): ลุยแพลนได้ไม่ต้องรออนุมัติ ยกเว้นเงิน/ทำลายล้าง
5. route ใหม่ต้อง `templates.TemplateResponse(request, name, ctx)` (starlette 1.x)
6. ทุกงานจบ: อัปเดต PLAN_STATUS.json + scp ขึ้น `YK_MVP/docs/` + จด CHANGELOG + memory

## Suggested skills (เซสชันหน้า)

- `superpowers:test-driven-development` — ทุก bugfix/feature (แนวที่ใช้มาตลอด เทสต์ 523+ ตัวเป็น safety net)
- `superpowers:verification-before-completion` — ก่อนอ้างว่าเสร็จ โดยเฉพาะหลัง deploy (marker + curl จริง)
- `debug-mantra` / `superpowers:systematic-debugging` — ถ้าโอรายงานบั๊ก
- `handoff` — ปิดเซสชันทุกครั้ง ส่งไม้แบบเดียวกับไฟล์นี้

## ความจริงที่เพิ่งพิสูจน์ (กันเชื่อของเก่าผิดๆ)

- "แตะ /uploads แล้ว Driver PWA พัง" = **เท็จ** (ปิด public ไปแล้ว ไม่มีอะไรพัง)
- "S5 รอบแรกยังไม่รัน" = **เท็จ** (รันแล้ว 4ก.ค. + ปิดข้อค้าง 6ก.ค. — เหลือแค่โอไล่รายชื่อ user; ระบบมี yk1 บัญชีเดียว ควรดันโอแยกบัญชี)
- เครื่อง Dev โอเป็นโน้ตบุ๊ก: **scheduled task ใหม่ต้องตั้ง AllowStartIfOnBatteries + StartWhenAvailable เสมอ** ไม่งั้นเงียบหายวันใช้แบต
