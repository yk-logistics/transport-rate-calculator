---
name: project-cy-kb-payout-calculator
description: หน้าคำนวณ KB โอนคืนเจ้าของงาน (CY/NHL/MOL/Siam) จาก invoice ใน Drive — กำลัง brainstorm/design 1ก.ค.
metadata: 
  node_type: memory
  type: project
  originSessionId: 9c311e54-7995-433c-9140-7be9415aba8a
---

**สถานะ:** หน้า **`/kb-payout` live บน server แล้ว 2 ก.ค.** (a4b6533 + เมนู "เงิน→🤝KB เจ้าของงาน" + **ติ๊ก "รับ KB แล้ว"** รายใบ/ทั้งชุดหลังจับคู่, ยกเลิกได้ — ตาราง `KbSettle` v32 create_all, จับคู่+ยอดค้างรับคิดเฉพาะใบที่ยังไม่ติ๊ก; verified table บน server) — โอใช้เองได้ไม่ต้องมี AI: กรอกยอดโอนจากสลิปธนาคาร → จับคู่ใบ+KB+ยอดโอนคืน 90%+ใบ ณ ที่จ่าย 3%; ไม่กรอก=ตารางทุกใบ. admin-only (permissions menu "kb"). ตรรกะอยู่ `app/services/kb_payout.py` (CLI tools/kb_payout.py ครอบตัวเดียวกัน). runbook ให้โมเดลถูก/คนอื่นทำแทน: `docs/KB_PAYOUT_RUNBOOK.md` (กฎ [[feedback-handoff-for-smaller-models]]). deploy: google-api-python-client ลง venv server + key JSON วางที่โฟลเดอร์แอป server; verified บน server: 35 ใบ, match 19,027.98 unique. CLI (commit 873fcfe): `list`=อินวอย CY ทุกใบ+KB, `match <ยอดโอน>`=subset-sum จับคู่ว่าลูกค้าโอนจ่ายใบไหน (ลองรับเต็ม/−1%เฉพาะขนส่ง/−1%/−3%). **ใช้จริงครั้งแรก: CY โอน 1ก.ค. 19,027.98 = CYIV2606-023(13,214.98)+026(5,963) หัก ณ ที่จ่าย 1% เฉพาะค่าขนส่ง — unique match; KB 1,713 โอนชาญณรงค์ 1,541.70 ใบ ณ ที่จ่าย 51.39.** โครงสร้างไฟล์อินวอย CY: ชีท[0] "ปะหน้าขนส่ง"=ยอดเดียวรวมทุกอย่าง (อย่าใช้), ชีท "ค่าขนส่ง"=ต่อตู้ J=ขนส่ง(5000) K=OT L=สำรองจ่าย M=รวม แถวตู้=A เป็นเลข เริ่มแถว16; cache ไฟล์ที่ tools/_kb_payout_cache (gitignored). **workflow โอ: อัปโหลดรูปสลิปโอน → รัน match → ได้ชุดใบ+ยอด KB.** **2ก.ค.ค่ำ (aa7b9ca): NHL/MOL/Siam i เสร็จ deployed** — parser นับแถวตู้ชีทค่าขนส่ง (หา col จากหัวตาราง), โฟลเดอร์เดือน M.YYYY ปี2026+, หน้าแยก section ต่อเจ้า + จับคู่ยอดโอนต้องเลือกเจ้าก่อน (dropdown/CLI arg); verified 100 ใบ CY35/NHL47/MOL16/Siam2, KB ค้าง NHL 32,230/MOL 5,600/Siam 300. ค้าง: ใบเสร็จ+ใบหัก ณ ที่จ่าย. เดิม=ต่างจาก KB ฝั่งคนขับ [[project-kb-driver-calc-price]] (live: `DailyJob.kb_amount` ลดฐานคิดเงินคนขับ).

**เป้าหมาย:** หน้า `/kb-payout` ใน MVP — เลือกลูกค้า→เดือน→invoice (lazy list จาก Drive) → คำนวณ KB ที่ต้องโอนเจ้าของงาน + ยอดรวม. **read-only ทั้งหมด ไม่แตะ DB/payroll**.

**มี KB 4 ลูกค้าเท่านั้น (โอยืนยัน):**
| ลูกค้า | สูตร KB | เจ้าของงาน (คนรับ KB) | บัญชี |
|---|---|---|---|
| CY | ΣJ(ค่าขนส่ง) − (ราคาเสนอ×ตู้) − OT_หักไม่ได้ | ชาญณรงค์ มาลีแย้ม | กสิกร 844-205-5344 |
| NHL | จำนวนตู้ × 110 | รุ่งโรจน์ เปรมปราชญ์ | ไทยพาณิชย์ 095-289-9898 |
| MOL | จำนวนตู้ × 100 | ทิติพร พิชิตสุรกิจ | กสิกร 0262730387 |
| Siam i | จำนวนตู้ × 50 | ทิติพร พิชิตสุรกิจ | กสิกร 0262730387 |

**สูตร CY (ยืนยันจาก invoice จริง):**
- ยอดวางบิล = คอลัมน์ **J** "ค่าขนส่ง" (=5000/ตู้) ไม่ใช่ M(รวมค่าล้าง/ค่าใช้จ่าย)
- ราคาเสนอ = เลขใน**ชื่อไฟล์** ก่อน `+` (เช่น `CYIV2605-001 MINKANG 4200` → 4200)
- OT หักไม่ได้ = เลขในชื่อไฟล์**หลัง `+`** (เช่น `...4600+100` → 100/ตู้เดียว); ไม่มี + = 0
- KB คิด**ยอดรวมทั้ง invoice** ไม่ต้องรู้ว่าตู้ไหนเสีย OT
- ตัวอย่าง: MINKANG 4200 (1ตู้) = 5000−4200−0 = **800**; JUN TAI 4600+100 (2ตู้) = 10000−9200−100 = **700**

**สูตร NHL/MOL/Siam:** KB = **นับแถวตู้ในชีทค่าขนส่ง × อัตราคงที่**. ชื่อไฟล์ไม่มีเลขราคา (เช่น `NHIV2606-001-Mitsubishi`). **ไม่มี OT หัก** (เฉพาะ CY). ชีท NHL คอลัมน์ต่างจาก CY (ค่าขนส่ง=H ไม่ใช่ J, แถวเริ่ม14) แต่ KB นับตู้อย่างเดียวไม่ต้องอ่านราคา.

**การแบ่งเงิน (ทุกลูกค้าเหมือนกัน, โอยืนยัน):**
- บริษัทเก็บ 10% ของ KB ; **โอนคืนเจ้าของงาน = KB × 90%**
- ใบหัก ณ ที่จ่าย 3% = **3% ของ KB เต็ม** (ออกใบเอกสารอย่างเดียว **ไม่ลบจากยอดโอน**)
- ตัวอย่าง MINKANG KB=800: เก็บ80, โอน**720**, ใบ ณ ที่จ่าย=24 (โอนเต็ม720 ไม่ลบ24)
- constants มีใน `services/kb.py` แล้ว: `KB_OUR_CUT=0.10`, `KB_WHT=0.03`

**อัตรา KB ต่อตู้ + ชื่อ/บัญชีเจ้าของงาน:** โออยากให้อยู่ใน**หน้าตั้งค่าในระบบ (แก้ได้ไม่ต้องแก้โค้ด)** — น่าจะต่อยอด `KbRule` (มี status_code/default_kb อยู่แล้ว) เพิ่ม owner name/bank.

**Drive:** อ่านผ่าน [[reference-google-drive-access]]. folder ปลายทาง = โฟลเดอร์ลูกค้าใน "ใบวางบิล LCB": CY `1aaiw4o9YJIW0sAqJk2-IoNqwmMWxHoCc`, NHL `1KhjrTAQw3aa9q-48RGbkx69JATIgUEbF`, MOL `1ZEPHu94U4hSQhutHpu90SF5_2Wq4lWhz`, Siam i `1cUePF2x0cXt-uilOjcpePYQe5uyUnGNi`.

related: [[reference-google-drive-access]] [[project-kb-driver-calc-price]] [[project-lcb-cy-kb-fulls]]
