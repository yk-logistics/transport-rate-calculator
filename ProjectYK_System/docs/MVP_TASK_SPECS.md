# สเปคลงมือรายงาน — คู่กับ "แพลน MVP" (MASTER_PLAN_2026-07.md)

> **เขียนโดย Fable 3 ก.ค. 2569 ตามคำสั่งโอ**: ละเอียดทุกงานจน Opus/Sonnet (หรือโมเดลเล็กกว่า)
> ทำได้ตรงเป้าโดยไม่ต้องเดา — อ่านไฟล์นี้คู่กับแพลนเสมอ ทำเสร็จ = ติ๊ก + อัปเดต % ในแพลน

---

## §0 กติกากลาง — บังคับทุกงาน (อ่านก่อนเริ่มทุกครั้ง)

1. **เริ่มงาน**: `git checkout -b feat/<ชื่องาน>` จาก main (ห้ามทำบน main); อ่าน CLAUDE.md + memory ที่เกี่ยว
2. **TDD**: เขียนเทสต์ก่อน (pattern มีให้ลอกใน `app/tests/` — fixture มาตรฐาน: temp sqlite + `appmod.init_db()` + login yk1/changeme1 + `YK_INSECURE_COOKIES=1`; ดูตัวอย่างครบใน `tests/test_kb_payout_page.py`)
3. **เงิน = โมเดลใหญ่เท่านั้น** (payroll/DailyJob เงิน/DB จริง): preflight ก่อน, `tools/net_guard.py before/after --allow <run>`, ห้ามเดา, DB server = ความจริง (local stale — **ห้าม push local DB**)
4. **Deploy**: probe ก่อนทับ (ดึงไฟล์ server เทียบ HEAD~1 ต้องตรง) → scp เฉพาะไฟล์ที่แก้ → restart แบบ kill-by-8010-PID (สคริปต์ตัวอย่างในไฟล์นี้ §0.1) → verify: marker ในไฟล์ server + logic probe ด้วย `.venv` ของ server + public 200 + พอร์ต 8020 (LINE) ยังรอด
5. **ปิดงาน**: เทสต์ทั้ง module ที่เกี่ยวผ่าน → commit (เฉพาะไฟล์ตัวเอง — ระวังไฟล์ session อื่นค้าง ดู `git status` ก่อน add) → deploy+verify → อัปเดต % ในแพลน + memory + runbook (กฎ handoff: เขียนให้เด็กกว่าทำต่อได้)
6. **schema ใหม่**: เพิ่ม model ใน `models.py` + import ใน `main.py` + bump `SCHEMA_VERSION` (ตารางใหม่ = create_all พอ ไม่ต้อง ALTER) — ดูตัวอย่าง KbSettle (v32)
7. **สิทธิ์hน้าใหม่**: เพิ่ม prefix ใน `app/permissions.py` MENUS+MATRIX + ลิงก์เมนูใน `templates/base.html` gate ด้วย `can_see(request, "<path>")` — หน้าเงิน/ลับ = admin เท่านั้น, การเงินทั่วไป = finance matrix
8. **Google Drive/Sheet**: อ่านผ่าน service account (key `noble-history-...json` — dev: ราก repo, server: โฟลเดอร์ app); **แก้ Sheet ต้องถามโอก่อน + ใส่ cell note ทุกช่อง** (กฎเหล็ก); ของแชร์แบบลิงก์ต้องเปิดจากรหัสโฟลเดอร์ (ค้นชื่อไม่เจอ)
9. **วันเวลา**: `| dmy` filter ใน template เสมอ; พูดถึงเวลา = ดูนาฬิกาจริง
10. **ภาษาไทยผ่าน ssh/console เพี้ยน** — verify ด้วย ASCII marker หรือเขียนไฟล์ UTF-8 แล้ว scp กลับ

### §0.1 สคริปต์ restart server (ใช้ซ้ำทุก deploy)
```powershell
Stop-ScheduledTask -TaskName YK_MVP_APP; Start-Sleep 2
$c = Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue
if ($c) { Stop-Process -Id $c.OwningProcess -Force }
Start-Sleep 1; Start-ScheduledTask -TaskName YK_MVP_APP; Start-Sleep 6
```
(scp .ps1 ขึ้นไปรันด้วย `-ExecutionPolicy Bypass -File` — ห้าม inline quote ผ่าน ssh มันพัง; server venv = `C:\Users\yklog\YK_MVP\app\.venv\Scripts\python.exe`)

---

## เฟส A — ปิดวงเงิน (เหลือ A2, A3; A1+A4 เสร็จ 3 ก.ค.)

### A2 ใบเสร็จรับเงิน + หนังสือรับรองหัก ณ ที่จ่าย จากหน้า KB — โมเดล: กลาง+ใหญ่รีวิวฟอร์ม (~1 วัน)
**เป้า:** หน้า /kb-payout กด "พิมพ์ใบเสร็จ+ใบหัก" ต่อชุดที่ติ๊กรับแล้ว → PDF 2 ใบ แทนทำมือ
**ก่อนเริ่ม (บล็อคเกอร์):** ขอโอส่งรูป/ไฟล์ใบเสร็จ+ใบหัก ณ ที่จ่ายที่ใช้อยู่จริง — **ห้ามเดาฟอร์มเอกสารภาษี**; ใบหัก ณ ที่จ่ายมีฟอร์มมาตรฐานสรรพากร (50 ทวิ) แต่ต้องเทียบของจริงโอก่อน
**ของที่มีให้ใช้:** fpdf2 + ฟอนต์ไทย: ดู `app/services/payroll_export_pdf.py` (มี _Pdf class + set_font_default ลอกได้เลย); ข้อมูลชุด = `KbSettle` (inv_no, kb_amount, transfer_amount, settled_on) + `CUSTOMERS` dict ใน `services/kb_payout.py` (ชื่อ/บัญชีเจ้าของงาน); เลข 90%/3% = `KB_OUR_CUT/KB_WHT`
**ขั้นตอน:** (1) เทสต์: route คืน PDF bytes + มีเลขถูก (2) service `kb_receipt_pdf.py`: build_receipt(settle_rows, owner) + build_wht_cert(...) (3) route GET `/kb-payout/receipt?invs=A,B` (admin) (4) ปุ่มบนหน้า kb_payout.html แถวสรุปชุดที่ settled (group by transfer_amount+วัน) (5) เลขที่เอกสารรันอัตโนมัติ: ตาราง `DocCounter` (doc_type, year, last_no) v33
**เกณฑ์ผ่าน:** โอเปิดชุดจริง 19,027.98 → PDF ใบเสร็จ 1,713 + ใบหัก 51.39 ตรงกับที่คำนวณ; พิมพ์ไทยไม่เพี้ยน (ตรวจด้วยตาบน PDF จริง ไม่ใช่ extract_text)

### A3 ติ๊ก "รับเงินแล้ว" หน้า AR sync กลับ Google Sheet — โมเดล: กลาง (~ครึ่งวัน)
**เป้า:** หน้า /finance/receivables ติ๊กรับแล้ว → ไฮไลท์แถวในชีท "รายการรับเช็ค" ให้ทีมอัตโนมัติ (เลิกทำ 2 ที่)
**เงื่อนไข:** ต้องได้คำอนุญาตโอก่อน (กฎ gsheet) + service account ต้องได้สิทธิ์ **Editor** บนไฟล์ 2 ตัว (ตอนนี้ Viewer ผ่านลิงก์โฟลเดอร์) — ขอโอเปลี่ยนแชร์ก่อนเริ่ม
**ขั้นตอน:** (1) gspread เปิดตามรหัสไฟล์ (id อยู่ใน `services/receivables.py` _fetch_register หาได้) (2) หา (แท็บ, แถว) จาก inv_no ที่ parser จำไว้ — เพิ่ม field `row_idx`+`tab` ใน parse_register (3) POST `/finance/receivables/mark` → เขียน fill เขียว `92D050` ทั้งแถว A..J + **cell note "ติ๊กจากระบบ <วัน> โดย <user>"** (4) เก็บสถานะฝั่งเราในตาราง `ArSettle` กัน sheet ล่ม
**เกณฑ์ผ่าน:** ติ๊กในระบบ → แถวในชีทเขียว+มีโน้ต ภายใน 5 วิ; ยกเลิกติ๊ก → สีออก; ระบบอ่านสีตัวเองรอบถัดไปไม่งง (received จาก fill ตรงกัน)

---

## เฟส B — รับงาน: ราคา + ปฏิทินรถ

### B1 ย้ายเครื่องคิดเรทเข้า /quote — โมเดล: Sonnet ทำได้ (สเปคชัด) + ใหญ่ตรวจเลข (~1 วัน)
**เป้า:** หน้า /quote ในระบบ คิดราคาขายเหมือน `TransportRateCalculator/transport_rate_calculator.html` (168KB single-file JS — โอยืนยันเป็นตัวจริง) ครบทุกช่อง
**วิธี:** **อย่า rewrite สูตร** — แตก HTML เดิม: เอา `<script>` + `<style>` มาวางใน template ใหม่ `templates/quote.html` ครอบด้วย base.html (เมนู "เงิน→📋 ใบเสนอราคา"); ตัดส่วนที่ชนกับ Tailwind ของ base ออกให้แสดงผลถูก; **เลขทุกตัวต้องเท่าหน้าเดิม** — เกณฑ์ผ่าน: กรอกอินพุตเดียวกัน 3 เคส (สั้น/กลาง/ไกล+ทางด่วน) ผลตรงหน้า GitHub Pages เป๊ะทุกบาท (screenshot เทียบ)
**สิทธิ์:** menu "quote" admin=edit, office=view? → เริ่ม admin เท่านั้น รอโอสั่งขยาย

### B2 เซฟใบเสนอราคา — โมเดล: Sonnet (~1 วัน)
**Model `Quotation` (v34):** id, customer_id?, customer_name, factory_name, location_url (ลิงก์กูเกิลแมพจากลูกค้า), origin_site (LCB/AYU/BIGC), km_round, toll_cost, cost_breakdown_json (เก็บอินพุต+เอาต์พุตเครื่องคิดทั้งก้อน), price_offered, price_agreed?, status (draft/negotiating/agreed/rejected), created_at, updated_at + ตาราง `QuotationAudit` (แก้ราคา = insert ประวัติ ห้าม update ทับ — ลอก pattern `DepositAudit`)
**UI:** ปุ่ม "เซฟ" ในหน้า /quote (JS โพสต์ค่า form+ผลลัพธ์) + หน้า /quote/list ค้นหาตามลูกค้า/โรงงาน/สถานะ + หน้าเดี่ยวแก้สถานะ/อัปเดตราคาต่อรอง
**เกณฑ์ผ่าน:** เซฟ→ปิดเบราว์เซอร์→เปิดใหม่→โหลดใบเดิมกลับเข้าเครื่องคิดได้ค่าเดิมครบ; แก้ราคา 2 ครั้งเห็นประวัติ 2 แถว

### B3 ราคาไหลเข้าเดลี่/บิล — โมเดล: **ใหญ่เท่านั้น (เงิน)** (~1 วัน)
**เป้า:** คีย์เดลี่แล้วระบบเสนอราคาจากใบเสนอที่ status=agreed (match ลูกค้า+ปลายทาง) — **เสนอ ไม่ auto-ทับ** (คนคีย์กดรับ); หน้า billing เตือนแถวที่ราคาไม่ตรงใบเสนอ
**จุดเสียบ:** `/api/daily-jobs/suggest` มีอยู่แล้ว (ดู logic เดิมก่อน) — เพิ่มแหล่ง Quotation; ห้ามแตะ engine เงินเดือน
**เกณฑ์ผ่าน:** เทสต์: มีใบ agreed → คีย์เดลี่ลูกค้า+เส้นทางตรง → ช่องราคาถูก prefill; ไม่มีใบ → พฤติกรรมเดิมเป๊ะ; net payrun ทุก run เดิม (net_guard)

### B4 ปฏิทินกำลังรถ /calendar — โมเดล: Sonnet โครง + ใหญ่รีวิวกติกา (~1.5 วัน)
**เป้า:** มุมมองเดือน/สัปดาห์ เลือกไซท์ (dropdown LCB/AYU/BIGC — โอ 3ก.ค.: แยกไซท์ เพราะมีหัวหน้าต่อไซท์) ต่อวันแสดง: รถทั้งหมด (Vehicle active ของไซท์) − จองแล้ว (DispatchPlan วันนั้น — อ่านโครงจาก `/dispatch/planner` ก่อนเขียน) − ซ่อม (MaintRecord เปิดอยู่/PM ครบกำหนดวันนั้น) − คนขับลา = **ว่างรับงาน X คัน**; คลิกวัน → รายคัน+สถานะ+ปุ่มไปสร้างงานใน planner
**บันทึกลา (โอให้ออกแบบ):** ทำ `LeaveRecord` มีตารางอยู่แล้วใน models (ตรวจ schema จริงก่อน) — เพิ่มปุ่มลงลาเร็วจากหน้า calendar (คน, วันเริ่ม-จบ, ชนิด) **และ** sync จากเดลี่: แถว leave_status/คำ "ลาหยุด" ใน destination ที่ทีมคีย์อยู่แล้ว ให้ตัว import สร้าง LeaveRecord อัตโนมัติ (สองทางเข้าหนึ่งตาราง)
**เกณฑ์ผ่าน:** วันที่มีข้อมูลจริง (เทียบมือ 3 วัน): เลขว่าง = นับมือตรง; รถซ่อม/คนลาโผล่ถูกวัน; โหลด < 2 วิ (คำนวณช่วงเดือนเดียว query รวมไม่วนต่อวัน)

---

## เฟส C — วางบิลอัตโนมัติ + ค่าเที่ยวตกหล่น

### C1 เช็คความครบก่อนวางบิล — โมเดล: Sonnet (~ครึ่งวัน)
หน้า /billing เพิ่มแถบ "พร้อมวางบิล?" ต่อลูกค้า+เดือน: นับแถวเดลี่ที่ (ราคา=0/ว่าง), (ไม่มีเลขใบงาน), (ซ้ำ วัน+ทะเบียน+ตู้), (ราคา≠ใบเสนอ ถ้ามี B3) → ลิสต์คลิกไปแก้ใน grid ได้; เกณฑ์ผ่าน: จับเคสจริงที่รู้อยู่แล้ว (BigC ราคา 9%) ขึ้นครบ

### C2 ออกใบวางบิลจากระบบ — โมเดล: **ใหญ่ออกแบบ+Sonnet ทำฟอร์มต่อ** (~2 วัน เริ่มลูกค้าประจำ: KMMT/เคอรี่(KLND), KAO, KTL, NHL, Nippon ยาง, PX19, CJ, CY, งานวาฬ, JGL)
**ขั้นตอน:** (1) ดูดโครงจากไฟล์จริง: ใบวางบิลทุกลูกค้ามีตัวอย่างใน Drive "ใบวางบิล LCB/<ลูกค้า>/<เดือน>" — เปิด 2-3 ใบ/ลูกค้า สรุปฟอร์ม (คอลัมน์/หัว/ท้าย) ลงไฟล์ spec ย่อยก่อนเขียนโค้ด (2) สร้าง `services/invoice_builder.py`: เลือกลูกค้า+ช่วง → ดึงเดลี่ → เติมฟอร์ม xlsx ด้วย openpyxl จาก **template ไฟล์จริง** (copy ไฟล์เดือนก่อนแล้วแทนค่า — อย่าเขียน layout จากศูนย์) (3) เลขแบบ INV รันต่อจากของจริง (`<ปธ.>IV<YYMM>-<seq>` ดู pattern ใน receivables) (4) หน้าปุ่มสร้าง+ดาวน์โหลด; ยังไม่เขียนเข้า Sheet อัตโนมัติ (รอโอ) (5) ลูกค้าแรกให้ทำ **CY** (ฟอร์มเรารู้ลึกสุดจากงาน KB — 2 ชีท ปะหน้า+ค่าขนส่ง)
**เกณฑ์ผ่าน:** ใบที่ระบบออกสำหรับเดือนที่ผ่านมา = ไฟล์จริงที่ทีมทำมือ ทุกตัวเลข (เทียบอัตโนมัติด้วยสคริปต์ ต่อลูกค้าอย่างน้อย 1 เดือนย้อนหลัง)

### C3 Oatside เข้าระบบ (สเปคละเอียดอยู่ในแพลนแล้ว) — โมเดล: ใหญ่ wiring+ตรวจเลข (~1 วัน)
เพิ่มเติมจากแพลน: (1) vendor `Oatside/build_oatside_reports.py` → `app/services/oatside_engine.py` **ห้ามแก้เนื้อ** (คอมเมนต์หัวไฟล์: vendored จากไหน วันไหน sync ยังไง) + copy `oatside_config.json`, `oatside_billing_overrides.json` ไป `app/` (2) route GET/POST `/oatside` (admin): อัปโหลด 2 xlsx → เซฟ `_oatside_uploads/<ts>/` → เรียก parse_legs→build_trips→pricing → เก็บผล json ล่าสุด (3) template: ตารางต่อวัน (เที่ยว, เรท, surcharge 50/100, blank run, รวม) + ปุ่มดาวน์โหลด xlsx เดิม (เรียก writer เดิมได้) (4) **เกณฑ์ผ่านตายตัว: อัปโหลดไฟล์เดือน เม.ย./พ.ค. ที่มีรายงานจริงแล้ว → ยอดรวมตรงรายงานเดิมทุกบาท**

### C4 ระบบค่าเที่ยวตกหล่น (โอสั่ง 3ก.ค.) — โมเดล: **ใหญ่เท่านั้น** (~1 วัน)
**โจทย์:** บางลูกค้าเดาราคา/เว้นราคาไว้ก่อนเพื่อจ่ายคนขับ พอวางบิลจริงค่อยรู้ราคา → ต้องจ่ายเพิ่ม/หักคืนคนขับย้อนหลัง; รอบเก่า finalized ห้าม recompute (สดย่อยจะหาย — บั๊กที่รู้แล้ว)
**ดีไซน์:** ตาราง `PayAdjustment` (v35): employee_id, source_run_id (รอบที่เกิดเหตุ), daily_job_id?, amount (+จ่ายเพิ่ม/−หักคืน), reason, status (pending→applied), applied_run_id — engine ตอน compute รอบใหม่: ดูด pending ของ emp เข้า other_income/other_deduction + mark applied; หน้า /payroll/<id> โชว์บรรทัด "ตกหล่นจากรอบก่อน"; ปุ่มสร้างจากหน้าแก้เดลี่: แก้ราคา/ค่าเที่ยวของแถวในรอบ finalized → เสนอ adjustment อัตโนมัติ (ต่าง = ใหม่−เก่า ตาม pay_mode: trip=Δtfd, mao=Δ(price−kb)×rate)
**เกณฑ์ผ่าน:** เทสต์ 3 เคส (trip จ่ายเพิ่ม/mao หักคืน/ไม่มี pending = engine เดิมเป๊ะ) + เคสจริงแรก: ถ้าโอแก้ราคา AYU ที่ปิดไปแล้ว

---

## เฟส D — มุมมองผู้บริหาร

### D1 เติมราคาเดลี่ทุกไซท์ — งานข้อมูล ไม่ใช่โค้ด — โมเดล: ใหญ่คุมโอทำ (~1 วันร่วมกับโอ)
รายงานแถวไร้ราคาต่อไซท์/ลูกค้า (query สำเร็จรูปให้โอไล่เติม — ใช้ C1 ได้เลยเมื่อเสร็จ); เกณฑ์: %priced ต่อไซท์ ≥95% (ปัจจุบัน LCB 63/BigC 9)

### D2 เงินหมุน/งบดุลย่อ /finance/cashflow — โมเดล: ใหญ่ (~1.5 วัน)
**แหล่งที่มีแล้ว:** AR (receivables summarize — เงินเข้า+วันนัด), payroll รอบถัดไป (ประมาณจากรอบล่าสุด), Loan+amortization (ดอกเบี้ย/งวด มีใน finance.py แล้ว)
**ต้องเพิ่ม:** ตาราง `DebtAccount` (v36): ชื่อ, ชนิด (บัตรเครดิต/OD/เงินกู้ส่วนตัว/ไฟแนนซ์), วงเงิน, ยอดค้าง, ดอกเบี้ย%, วันตัดรอบ/วันจ่าย, จ่ายขั้นต่ำ — **ให้โอกรอกเองผ่านหน้า CRUD ง่ายๆ** (ข้อมูลส่วนตัว ไม่มีในระบบ)
**เอาต์พุต:** ตาราง 8 สัปดาห์ล่วงหน้า: เข้า (AR ตาม DUE) − ออก (เงินเดือนตามรอบ 3 ไซท์ + งวดหนี้ทุกก้อน + ค่าใช้จ่ายเฉลี่ยจาก petty) = ยอดสะสม; สัปดาห์ติดลบ = แถบแดง
**เกณฑ์ผ่าน:** โอดูแล้วบอกได้ว่า "สัปดาห์ไหนตึง" ตรงกับความรู้สึกจริง; เลขทุกแหล่งคลิกย้อนไปหน้าที่มาได้

### D3 ต้นทุนต่อคัน — โมเดล: Sonnet+ใหญ่รีวิว (~1 วัน)
รวมต่อทะเบียน/เดือน: รายได้ (เดลี่) − น้ำมัน (FuelTxn) − ซ่อม (MaintRecord) − ค่าเที่ยวคนขับ − งวดรถ (จาก DebtAccount ชนิดไฟแนนซ์ ผูกทะเบียน) = กำไร/คัน เรียงแย่สุดขึ้นก่อน + sparkline 6 เดือน; หน้ามีอยู่บางส่วนที่ /finance/vehicles — ตรวจของเดิมก่อน ต่อยอดไม่ทำซ้ำ

---

## เฟส F — LINE เข้าระบบ (สเปคหลัก)

**พื้นฐานทุกข้อ:** DB `C:\Users\yklog\YK_LINE_ARCHIVER\line_archive.db` (ตาราง line_group 44 / line_user 196 / line_message: id, line_message_id, group_id, user_id, msg_type, text, media_path, sent_at, received_at) + media `line_media/`; **MVP เปิดแบบ read-only เท่านั้น** (`sqlite3 file:...?mode=ro` หรือ engine แยก) — **ห้ามเขียน DB นี้เด็ดขาด** (ของ service 8020); dev ไม่มีไฟล์นี้ → เทสต์สร้าง DB จำลอง schema เดียวกัน

### F1 หน้า /line ค้นหาย้อนหลัง — โมเดล: Sonnet (~1 วัน)
(1) `services/line_archive.py`: search(q, group_id?, msg_type?, since?, limit=200 + pagination), groups_by_activity() (2) route /line (สิทธิ์: menu "line" admin=edit office=view) + /line/media/{id} เสิร์ฟไฟล์ (ตรวจ path traversal! media_path ต้องอยู่ใต้ line_media จริง) (3) UI: ช่องค้น + ผลลัพธ์ (กลุ่ม/คน/เวลา/ข้อความ, รูป=thumbnail คลิกขยาย) + แท็บ "กลุ่มตามความเคลื่อนไหว" ล่าสุด→เงียบ; **เกณฑ์ผ่าน:** ค้นคำที่รู้ว่ามี (เช่น ทะเบียนรถ) เจอในทุกกลุ่มที่เกี่ยว < 2 วิ; เปิดรูปเก่าเดือน มิ.ย. ได้

### F2 กล่องงานเข้า — โมเดล: ใหญ่ออกแบบ rule + Sonnet ทำหน้า (~1 วัน)
สแกน line_message กลุ่มที่ mark เป็น "ลูกค้า" (เพิ่มคอลัมน์ mapping ฝั่ง MVP: ตาราง `LineGroupMap` group_id↔customer/site/ชนิด — **เก็บฝั่ง app.db** ไม่แตะ DB archiver) หา pattern งาน (มีวันที่+เวลา / เลขตู้ TEXU… 11 หลัก / คำ "เข้า","โหลด","ส่ง") → หน้า inbox แสดง candidate → ปุ่ม "รับเป็นงาน" เปิด dispatch planner พร้อม prefill + จำ line_message_id กันเด้งซ้ำ; **เกณฑ์ผ่าน:** ทดสอบกับข้อความจริงย้อนหลัง 1 สัปดาห์ — จับงานจริงได้ ≥80%, false positive มีปุ่ม "ไม่ใช่งาน" แล้วไม่โผล่ซ้ำ

### F3 ชุดหลักฐานวางบิล (POD) — โมเดล: ใหญ่ (~1.5 วัน หลัง F1+C2)
รูปในกลุ่ม → เสนอผูก DailyJob: filter กลุ่ม↔ลูกค้า (LineGroupMap) + วัน sent_at = work_date ±1 + ทะเบียน/เลขตู้ใน text ใกล้เคียง (ข้อความก่อนหน้าในกลุ่มเดียวกัน 10 นาที) → หน้า review จับคู่ (ยืนยัน/เปลี่ยนงาน/ข้าม) → ตาราง `JobMedia` (daily_job_id, line_message_id, kind) → หน้า "เอกสารต่อลูกค้า+ช่วง" รวมรูป+ใบวางบิล (C2) → ZIP; **เกณฑ์ผ่าน:** ลูกค้า 1 ราย 1 รอบจริง: ครบทุกเที่ยว ≥90% โดยกดยืนยันไม่เกิน 1 คลิก/รูป

### F4 น้ำมันจากไลน์ — โมเดล: ใหญ่ (เงินใกล้ตัว) (~1 วัน)
กลุ่มปั๊ม/น้ำมัน: รูปสลิป + xlsx จากปั๊ม → เทียบ FuelTxn (วัน+ทะเบียน+ยอด±5) → รายการ "มีสลิปแต่ไม่มีในระบบ / มีในระบบแต่ไม่มีสลิป" — **รายงานอย่างเดียว ไม่แก้เงินอัตโนมัติ**; reuse ตัวอ่าน xlsx ปั๊ม (ถ้าฟอร์แมตเดียวกับไฟล์ที่ 15 ไฟล์ใน media — เปิดดูจริงก่อน)

### F5 digest เช้า — โมเดล: Sonnet (~ครึ่งวัน หลัง F1)
สรุปต่อกลุ่มสำคัญ (ลิสต์กลุ่มจาก LineGroupMap): จำนวนข้อความ/รูปเมื่อวาน + ข้อความแรก-สุดท้าย + กลุ่มเงียบ >3 วัน → หน้า /line/digest + (ถ้าโอต้องการ) ยิงเข้า Discord ช่องสรุป (มี discord_api ใน line_archiver แต่**ห้าม import ข้าม service** — copy ฟังก์ชัน post เดียวพอ)

### F0 (เลือกได้ ปลอดภัย) จัดหมวด Discord ให้กลุ่มใหม่อัตโนมัติ — Sonnet (~1 ชม.)
สาเหตุที่ห้องใหม่ไม่เข้าหมวด: โค้ดจัดหมวดอยู่ใน branch `feat/line-archiver-discord-categories` **ยังไม่ merge + ยังไม่ deploy ไป archiver บน server** — งาน: merge → scp ไฟล์ที่เปลี่ยน (archiver.py, categories.py, discord_api.py, db.py) ไป `C:\Users\yklog\YK_LINE_ARCHIVER` → `nssm restart YKLineBot` → ทดสอบด้วยกลุ่มทดสอบใหม่ 1 กลุ่ม; ความเสี่ยงต่ำ (จัดหมวด best-effort พังก็แค่ไม่จัด ไม่กระทบเก็บข้อความ — มี retry + DB เก็บก่อน forward เสมอ)

---

## เฟส E — สนาม (สเปคย่อ — ทำท้ายสุด รายละเอียดค่อยขยายตอนถึง)

E1: ต่อยอด Driver PWA เดิม (`/driver/*` + DriverSubmission + รีวิวที่ /admin/submissions — อ่านของเดิมก่อน): เพิ่มชนิด submission เช็คอิน 3 จุด (พิกัดจากเบราว์เซอร์) + รูปตู้ 4 ด้าน + ปิดงาน; ผูก DailyJob วิธีเดียวกับ F3
E2: รายงานน้ำมันผิดปกติ: ต่อยอด `tools/fuel_slip_reconcile.py` + กติกา (เติมถี่ผิดปกติ/ลิตรเกินถัง/นอกเส้นทางเวลา) → หน้าอ่านอย่างเดียว + ธงบนสลิป

---

## เฟส G — ดูแลเครื่อง/พื้นที่ (โอสั่ง 3ก.ค.)

### G1 การ์ดสุขภาพเครื่อง + เตือนพื้นที่ — โมเดล: Sonnet (~ครึ่งวัน)
**เป้า:** โอเห็นสถานะเครื่องในระบบเอง ไม่ต้องรอถาม
(1) route `/admin/server-health` (admin) + การ์ดย่อบนหน้าแรก: พื้นที่ดิสก์ ใช้/เหลือ/%, ขนาด line_media, ขนาด backups, วันที่ backup DB ล่าสุด, สถานะ 8010/8020 — อ่านด้วย `shutil.disk_usage` + `Path.stat` (เครื่องเดียวกันหมด)
(2) เตือน: เหลือ <20% = แถบเหลือง, <10% = แดง + แจ้งเข้า Discord ช่อง alerts (ลอก pattern `line_archiver/health_poll.py` — แจ้งเฉพาะตอนเปลี่ยนสถานะ ไม่ spam)
(3) กติกามาตรฐานที่มือโปรใช้ (ใส่ในหน้าเดียวกันเป็นข้อความ): threshold 80/90%, retention backups 14 วัน (มีแล้ว), archive media เก่า
**เกณฑ์ผ่าน:** ตัวเลขบนหน้า = ที่เช็คมือด้วย PowerShell เป๊ะ; ลองย้าย threshold ให้ต่ำกว่าค่าจริง → เตือนขึ้น+เข้า Discord 1 ครั้ง

### G2 Archive สื่อ LINE เก่า (ทำเมื่อใกล้เต็มจริง — ยังไม่เร่ง เหลือ 187 GB)
สคริปต์ย้าย line_media เก่ากว่า 6 เดือน → External HDD/Google Drive + อัปเดต media_path ใน DB ให้ชี้ที่ใหม่ (ตอนนี้แค่จorganiseสเปคไว้ ยังไม่ทำ)

## เฟส S — ความปลอดภัยทุกมิติ (โอสั่ง 3ก.ค. "ไม่ถนัด ให้ออกแบบให้") — โมเดล: ใหญ่นำ (~2 วัน)

> ฐานที่ทำแล้ว (red-team 15 มิ.ย. — ดู docs/SECURITY_FOR_OAT.md + memory reference-mvp-server-deploy):
> SSH key-only+จำกัดวง Tailscale, Firewall/Defender/UAC เปิด, RDP ปิด, XAMPP ปิด, รหัสผ่าน bcrypt,
> กันเดารหัส (ล็อก user+IP), คุกกี้ Secure/HttpOnly/8ชม., HSTS/X-Frame/nosniff, RBAC 4 บทบาท

### S1 สำรองข้อมูลนอกเครื่อง (สำคัญสุด — กันไฟไหม้/ransomware/ดิสก์พัง) 
ตอนนี้ backup อยู่ในเครื่องเดียวกับของจริง! งาน: task กลางคืน zip (app.db + line_archive.db + .env ทั้งคู่ + เอกสารสำคัญ) → อัปโหลด Google Drive ผ่าน service account (โฟลเดอร์ใหม่แชร์แบบจำกัด) เก็บ 30 วันหมุนเวียน + ทดสอบ restore จริง 1 ครั้ง (backup ที่ไม่เคย restore = ไม่มี backup); เตือนเข้า Discord ถ้าคืนไหนพลาด
### S2 ตรวจภายในแอป
เพิ่ม audit log การกระทำเงิน (ใคร finalize/แก้ราคา/ติ๊ก KB เมื่อไหร่ — หลายจุดมีแล้ว: DepositAudit/DailyJob audit → เก็บให้ครบทุกจุดเงิน), เช็ค upload ทุกช่อง (นามสกุล+ขนาด+ห้าม execute), path traversal ทุก route ที่เสิร์ฟไฟล์ (F1 มีระบุแล้ว), ปิด directory listing
### S3 ของลับ
ย้าย token/secret ที่ยังอยู่ในไฟล์ .bat/.env กระจัดกระจาย → ไฟล์เดียว จำกัดสิทธิ์; หมุน (rotate) LINE/Discord token + รหัส service account ปีละครั้ง; ตรวจว่า key Google (yk-sheets-editor) มีสิทธิ์แค่ไฟล์ที่จำเป็น
### S4 คน (ช่องโหว่ใหญ่สุดของจริง)
เอกสาร 1 หน้าให้ทีม: ห้ามแชร์รหัส, สังเกต phishing, เครื่องที่ล็อกอิน MVP ต้องมี Defender เปิด; บัญชีใครออกจากงาน → disable ทันที (มีปุ่มแล้วที่ /admin/users)
### S5 ทดสอบเจาะซ้ำทุกไตรมาส
รัน checklist red-team เดิม (พอร์ตเปิด/บริการแปลก/สิทธิ์ไฟล์/dependency เก่า `pip list --outdated` เทียบ CVE) — เขียนเป็น runbook ให้โมเดลเด็กรันได้

## การวัด "จบ 100% ใช้จริง" ของทั้งระบบ
ทุกเฟสเสร็จ + โอทำงานจริง 1 รอบเดือนเต็มโดย **ไม่เปิด Excel ทำมือเลย** (ยกเว้นชีทเดลี่ที่ทีมคีย์) = ประกาศ 100%
