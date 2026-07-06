---
name: project-ayu-jul-import-ready
description: "AYU รอบ 2026-07 ✅ import แล้ว 6ก.ค. (314 งาน+60 น้ำมัน จากชีทจริง) — กติกา: แก้ที่ชีทจริงเท่านั้น แล้ว re-import --wipe-prior เพิ่มได้; ห้าม wipe ถ้าทีมเริ่มแก้ grid"
metadata: 
  node_type: memory
  type: project
  originSessionId: d4a29959-9dce-4e25-82a7-9d031c3c20be
---

Preflight 4 ก.ค. 2026 (read-only ทั้งหมด — ยังไม่ import):

- **ต้นทางพร้อม:** xlsx พี่หวาน (Drive id 1vQ0l2Rt…) มีแท็บ **Jul 26 = 103 แถว คีย์ถึง 5 ก.ค.** + Jun 26 ครบถึง 30 มิ.ย.; **ชีทจริง** (1F5eJlYs…) มีแท็บ Jul 26 แล้ว 123 แถว = มีคน sync/คีย์ตรงแล้ว
- **เครื่องมือพร้อม (commit แล้ว):** `tools/import_ayu_daily.py` รองรับ `--cycle 2026-07` (อ่าน 2 แท็บ: ท้าย Jun 26 สำหรับ 26-30 มิ.ย. + Jul 26; window 26 มิ.ย.–25 ก.ค.) + env `YK_AYU_XLSX` ชี้ไฟล์เอง; **dry-run: jobs=231 fuel=35 ค่าขนส่ง 28,338 ค่าเที่ยว 29,379** (ยอดต่ำเพราะราคายังไม่คีย์เยอะ — งาน D1)
- **server ปลอด dupe:** AYU ใน DB จบ 25 มิ.ย. (ไม่มีใครคีย์รอบใหม่ใน grid)
- **ทางแยกที่หยุดรอโอ (กฎเงิน — workflow ambiguity จริง):** รอบ มิ.ย. import ตอน*จบรอบ* ครั้งเดียวแล้วแก้ต่อใน grid; ถ้า import **กลางรอบ**ตอนนี้จะปลดล็อค F3 (วัด POD)/D1/fuel line-compare ทันที **แต่**ต้องตกลงว่าจากนั้นข้อมูลรอบ ก.ค. แก้ใน grid เท่านั้น — ห้ามใครรัน re-import `--wipe-prior` ทับ (จะกินราคาที่ทีมเติมใน grid — บั๊กตระกูลเดียวกับ C4)

**Why:** เดลี่ ก.ค. คือตัวปลดล็อคงานแพลนที่เหลือ (F3 วัดรอบเต็ม, D1, fuel compare) — เตรียมครบเหลือโอพยักหน้า

**How to apply:** โอเคาะ "import เลย" → รันบน server: scp xlsx สด + tools 2 ไฟล์ → `YK_AYU_XLSX=<path> python import_ayu_daily.py --cycle 2026-07` (ไม่ dry-run) → แจ้งทีมกติกาห้าม re-import; โอเคาะ "รอจบรอบ" → รัน 26 ก.ค. แบบเดิม ดู [[project-ayu-daily-import]] [[project-f3-pod-measured-tuned]]

**✅ IMPORT แล้ว 6 ก.ค. ~17:20 (โอเคาะ "import ตอนนี้เลย เพิ่มทีหลังได้ — อยากดูรายได้คนขับปัจจุบันเฉลี่ยงาน"):**
- แหล่ง = **ชีทจริง 1F5eJlYs… export เป็น xlsx** (แก้ล่าสุด 6ก.ค. 16:05 — สดกว่า xlsx พี่หวานที่นิ่งตั้งแต่ 2ก.ค.; RUNBOOK ยืนยัน "ระบบ import จากชีทจริง")
- ผล: **314 งาน + 60 น้ำมัน** (ค่าขนส่ง 134,495.65 / ค่าเที่ยว 70,510.50) — verify: source rows=314 เป๊ะ, AYU 841→1,155, BIGC/LCB นิ่ง, fuel 1667→1727
- ไฟล์บน server: `YK_MVP/tools/` (ayu_gsheet.xlsx + import 2 ตัว + `_run_ayu_import.ps1` — env ตั้งในไฟล์ กัน gotcha env ข้าม ssh)
- **วิธี import เพิ่มรอบหน้า:** export ชีทจริงใหม่ → scp ทับ ayu_gsheet.xlsx → รัน `_run_ayu_import.ps1` (dry-run) ดูยอด → `-Apply` **พร้อม --wipe-prior** (แก้ ps1 เพิ่ม flag หรือรันมือ) — ปลอดภัยตราบใดที่ทีมแก้ข้อมูล AYU ที่ชีทจริงเท่านั้น ไม่แก้ grid