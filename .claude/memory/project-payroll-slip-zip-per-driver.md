---
name: project-payroll-slip-zip-per-driver
description: "Payroll print page — \"แยกไฟล์ต่อคน (ZIP)\" per-driver PDF; now server-side Chrome (Thai-correct), was broken html2canvas"
metadata: 
  node_type: memory
  type: project
  originSessionId: 09916d86-fbc0-4c5a-bfc8-46e13949f62c
---

ปุ่ม **"📦 แยกไฟล์ต่อคน (ZIP)"** ที่ `/payroll/{id}/print` (template `payroll_print_all.html`) — สร้าง PDF
สลิปแยกต่อคนขับ → ZIP **ดาวน์โหลดลงเครื่องโอ** (ไม่เซฟ server) เพื่อส่งต่อ LINE ให้คนขับ. รองรับ `?for=boss`.

**29มิ.ย. (รอบ 2) — แก้ไทยเพี้ยน + ย้ายมาทำฝั่ง server:** เวอร์ชันแรกใช้ **html2canvas** (ฝั่งเบราว์เซอร์,
`html2pdf.bundle.min.js`) raster DOM → **shape ภาษาไทยไม่เป็น วรรณยุกต์/สระลอยหลุดตัว** (เช่น "น้ำมัน"→"ใบ ขับ",
"เนื้อ"→"เนื อ"). บั๊กมีตั้งแต่แรก — "verified" รอบแรกพลาดเพราะ screenshot **DOM** (browser วาดถูก) ไม่ได้ดู **ตัว PDF
ที่ html2canvas สร้าง**. โอเจอตอนเปิดไฟล์ ZIP จริง.

**ทางแก้ที่ใช้ = Chrome headless ฝั่ง server** (`services/payroll_zip_pdf.py` + route `POST /payroll/{id}/export-zip`):
render `payroll_slip.html` ต่อคน → `chrome --headless=new --print-to-pdf` (ตัวเรนเดอร์จริง → **ไทยคมชัด** + layout
เหมือนหน้าสลิป รวม JS zoom ย่อ 1 หน้า/คน ที่ Chrome print honor `zoom`) → มัด `zipfile` → `Response` ZIP กลับ
(Content-Disposition `filename*=UTF-8''` percent-encode ชื่อไทย). UX โอเหมือนเดิมเป๊ะ: กดปุ่ม → ได้ ZIP ลงเครื่อง.
ลบโค้ด html2canvas/JSZip CDN ทิ้งหมด. **fpdf เดิม (`payroll_export_pdf.py` / ปุ่ม export-pdfs) ยังอยู่ ไม่แตะ.**

**3 GOTCHA Chrome→PDF บน Windows (เสียเวลา debug นานสุด → ดู [[reference-chrome-headless-pdf]]):**
1. ต้องมี `--user-data-dir` เฉพาะ ไม่งั้น Chrome โยนงานให้ instance ที่เปิดอยู่แล้วไม่ render.
2. `chrome.exe` คืน exit 0 **ก่อน** child เขียน PDF เสร็จ ~0.7s → **poll หาไฟล์** ไม่ใช่เช็คครั้งเดียว.
3. **ห้าม `tempfile.TemporaryDirectory`/`mkdtemp`** (ACL 0o700 → Chrome เขียน PDF ไม่ได้ ค้างจน timeout) — ใช้ plain
   `mkdir` ใต้ `app/_pdf_tmp/<uuid>` แล้ว `shutil.rmtree` เอง (gitignored).

**verified จริงปลายทาง:** local run#2 (LCB มิ.ย. 18 คน) ZIP 18 PDF ไทยถูกทุกตัว (เทียบภาพเดิมเพี้ยน หายสนิท); **บน
server ทดสอบ Chrome render ได้ทั้ง user `yklog` และ account จริงที่แอปรัน = `NT AUTHORITY\SYSTEM` (YK$) → PDF_OK 50KB**
(SYSTEM เป็นจุดเสี่ยงสุดเพราะ session-0/no-profile แต่ผ่าน). deploy ผ่าน `deploy_mvp.sh --markers "export-zip"` 6 เช็ค PASS.

**เพิ่มหน้าสรุปผู้บริหาร (same commit):** ตาราง summary ใน `?for=boss` มีคอลัมน์ **วางบิล / KB / น้ำมัน(รวมทุกบิล) /
น้ำมัน% / คนขับ / คนขับ%** — รายได้คนขับ=`gross_total−fuel_cost_self` (เหมา=ค่าเที่ยว−น้ำมัน, เที่ยว=เงินเดือน+ดูแลรถ+
เที่ยว ตรงทั้งคู่), % เทียบฐาน **วางบิลหลังหัก KB** (`Σrevenue_customer − Σkb_amount`). เลขหลุดเกณฑ์ = **แดง** (น้ำมัน>50%,
คนขับ<15%) ให้ตรวจไวๆ ด้วยตา. หน้าคนขับ (ไม่ใช่ boss) ไม่โชว์คอลัมน์พวกนี้. ข้อมูลมาจาก slip_ctx ที่ build อยู่แล้ว
(ไม่ query เพิ่ม). **แค่แสดงผล ไม่แตะเงิน** — net/payrun ทุกไซต์เท่าเดิม, tests 24 pass.

related: [[reference-chrome-headless-pdf]], [[project-payroll-bank-print]], [[feedback-merge-and-deploy-without-preview]], [[reference-deploy-mvp-selfverify]], [[project-kb-driver-calc-price]]
