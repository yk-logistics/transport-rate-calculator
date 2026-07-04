---
name: reference-chrome-headless-pdf
description: "Render HTML→PDF/PNG server-side with headless Chrome (Thai-correct, unlike html2canvas) — 3 Windows gotchas"
metadata: 
  node_type: memory
  type: reference
  originSessionId: d58e4e18-00ba-4662-8e31-6bae44738545
---

วิธีแปลง HTML → PDF (หรือ PNG) **ฝั่ง server** ที่ภาษาไทยถูกต้อง: ใช้ **headless Chrome** ไม่ใช่ html2canvas/jsPDF.
- **html2canvas raster DOM แล้ว shape ไทยไม่เป็น** (วรรณยุกต์/สระลอยหลุดตัว) — แก้ไม่ได้ ไม่ว่าฝังฟอนต์/ปรับ scale.
- **Chrome `--print-to-pdf` ใช้ตัวเรนเดอร์จริง** → ไทยคมชัด + honor CSS `zoom` (เช่น JS ย่อ 1 หน้า/คน) + รัน JS/รอ load.
- โค้ดตัวอย่างใช้งานจริง: `ProjectYK_System/app/services/payroll_zip_pdf.py` (`find_chrome`, `html_to_pdf_bytes`).

เครื่อง dev (.178/HOME) + server (.197) **มี Chrome ทั้งคู่** ที่ `C:\Program Files\Google\Chrome\Application\chrome.exe`
(server ไม่มี Edge). flags: `--headless=new --disable-gpu --no-sandbox --no-first-run --user-data-dir=<uniq>
--print-to-pdf=<out> --print-to-pdf-no-header --virtual-time-budget=10000 file:///<src>`.

**3 GOTCHA บน Windows (เสียเวลา debug จริง):**
1. **ต้องมี `--user-data-dir` เฉพาะต่อ call** — ถ้าไม่ใส่ Chrome ที่เปิดอยู่ (โอเปิด browser อยู่ ~13 proc) จะรับงาน
   แทนแล้ว launcher ออกทันที **ไม่ render**.
2. **`chrome.exe` คืน exit 0 ก่อน child เขียนไฟล์เสร็จ ~0.7s** (launcher แยกจาก render child). `subprocess.run` คืนแล้ว
   ไฟล์ยังไม่มี → **ต้อง poll หาไฟล์** (รอจน size นิ่ง) ไม่ใช่เช็ค `out.exists()` ครั้งเดียว. (PowerShell `Start-Process -Wait`
   ไม่เจอบั๊กนี้เพราะมันรอทั้ง tree — แต่ Python `subprocess` เจอ.)
3. **ห้าม `tempfile.TemporaryDirectory` / `mkdtemp` เป็น work dir** — มัน set ACL **owner-only 0o700** แล้ว Chrome render
   child (โดยเฉพาะ `--no-sandbox` / รันใต้ SYSTEM) **เขียน PDF ไม่ได้ → ค้างจน timeout 60s**. พิสูจน์: input เดียวกัน render
   1.4s จาก dir ที่ `Path.mkdir()` ปกติ แต่ค้าง 60s จาก TemporaryDirectory (location/nesting ไม่เกี่ยว). **ใช้ plain `mkdir`
   ใต้โฟลเดอร์แอป (เช่น `app/_pdf_tmp/<uuid>`) แล้ว `shutil.rmtree` เองใน finally.**

**SYSTEM account OK:** แอป MVP รันเป็น scheduled task `NT AUTHORITY\SYSTEM` (proc owner = `YK$`). Chrome headless render
ไทยได้ใต้ SYSTEM (เทสต์แล้ว PDF_OK ~50KB) — แม้ session-0/ไม่มี user profile. วิธีเทสต์ as-SYSTEM: register scheduled task
`-Principal SYSTEM` ชี้ python script ที่เขียนผลลง `C:\Windows\Temp` (user home เขียนไม่ได้จาก SYSTEM task), Start แล้วอ่านไฟล์.

PDF text-extract (pypdf) ของ Chrome **อาจ drop ไทย combining marks** ที่ text layer — **ไม่ใช่บั๊กการแสดงผล** (glyph บนหน้า
ถูก). อย่าตัดสินด้วย extract_text — **ต้อง render เป็นภาพแล้วดูตา** (`--screenshot=out.png`). pymupdf/pdf2image ไม่ได้ลงใน venv.

related: [[project-payroll-slip-zip-per-driver]], [[reference-deploy-mvp-selfverify]], [[reference-mvp-deploy-restart-gotcha]]
