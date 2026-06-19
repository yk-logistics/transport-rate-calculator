# Slip-Reader — Runbook (ตั้งค่า → ทดสอบ → deploy)

อ่านสลิปโอนจากกลุ่ม LINE "Y.K. หัวลาก LCB" → ร่างรายการสดย่อย → ส่งเข้า MVP
(`/api/petty/ingest`) เป็นสถานะ `pending_review` → หมิว/แอดมินอนุมัติที่ `/petty/review`.

**ขอบเขตเฟสนี้:** LCB ที่เดียว · ลง MVP DB เท่านั้น · **ไม่แตะ Google Sheet**.
ออกแบบ/เหตุผล: `docs/superpowers/specs/2026-06-18-lcb-slip-reader-review-design.md`.

---

## 0. สิ่งที่ต้องมีก่อน

| ของ | ได้จากไหน |
|-----|-----------|
| **ANTHROPIC_API_KEY** (`sk-ant-...`) | console.anthropic.com → API Keys → Create Key → เติมเงิน Billing ขั้นต่ำ $5 |
| **YK_SLIP_INGEST_TOKEN** | คิดเองสตริงสุ่มยาว ๆ (เช่น `openssl rand -hex 24`) — ต้องตั้ง**ค่าเดียวกัน**ทั้งฝั่ง MVP และ slip-reader |
| line_archive.db | มีอยู่แล้วบน server ที่ `C:\Users\yklog\YK_LINE_ARCHIVER\line_archive.db` |

> ⚠️ **API key = เงินจริง.** ห้าม commit เข้า git / ห้ามส่งในแชต-ไลน์. เก็บใน `.env` ที่ gitignored.
> ปริมาณจริง ~700 สลิป/เดือน (Haiku) = หลักไม่กี่บาท–สิบกว่าบาท/เดือน. ไม่ต้องอัป Max.

---

## 1. ทดสอบความแม่นก่อน (dry-run, เครื่อง dev — ยังไม่แตะ server/MVP)

พิสูจน์ว่า engine อ่านสลิปจริงแม่นไหม โดยรันกับสลิป proof 28 รูปที่เก็บไว้
(`reports/lcb_slips_0615/`) แล้วเทียบกับเฉลยใน `reports/lcb_petty_ai_accuracy_2026-06-18.md`.

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-...."
cd "C:\Users\guole\Desktop\2026.5.28\Desktop\Project YK\ProjectYK_System"
app\.venv\Scripts\python.exe -m slip_reader.dry_run_report
```

→ ได้ไฟล์ `reports/slip_reader_dryrun.md` (ตาราง file/is_slip/amount/recipient/memo/time).
**ตรวจ:** ยอด+ชื่อตรงกับเฉลยไหม, รูปที่ไม่ใช่สลิป (ใบงาน/แพลน/ตารางสรุป) ขึ้น is_slip=False ไหม.
ถ้าแม่นพอ → ไปข้อ 2. ถ้าเพี้ยน → แก้ prompt/schema ใน `slip_reader/engine.py` แล้วรันซ้ำ.

> ไฟล์ `slip_reader_dryrun.md` มีชื่อผู้รับเงิน — **อย่า commit** (gitignored แล้ว).

---

## 2. ตั้งค่าฝั่ง MVP (เปิดให้รับ slip ingest)

MVP ต้องรู้ token เดียวกัน ไม่งั้น endpoint จะตอบ 401.

- **dev:** ตั้ง env ก่อนสตาร์ตแอป
  ```powershell
  $env:YK_SLIP_INGEST_TOKEN = "<token เดียวกัน>"
  ```
- **server (MVP เป็น NSSM service):** เพิ่ม env var ให้ service
  ```powershell
  nssm set <MVPserviceName> AppEnvironmentExtra YK_SLIP_INGEST_TOKEN=<token>
  nssm restart <MVPserviceName>
  ```
  (ดูชื่อ service MVP จริงจาก `docs/MVP_SERVER_DEPLOY.md`).

ทดสอบว่า endpoint ตอบ: ส่ง payload ปลอม 1 ก้อนแล้วต้องได้ `{"status":"created"}` หรือ
`duplicate` (ยิงซ้ำ) — token ผิดต้องได้ 401.

---

## 3. รัน slip-reader (เครื่อง dev ทดสอบจริงก่อน)

```powershell
$env:ANTHROPIC_API_KEY    = "sk-ant-...."
$env:YK_SLIP_INGEST_TOKEN = "<token เดียวกับ MVP>"
$env:MVP_INGEST_URL       = "http://127.0.0.1:8010/api/petty/ingest"   # หรือ URL server
cd "C:\Users\guole\Desktop\2026.5.28\Desktop\Project YK\ProjectYK_System"
app\.venv\Scripts\python.exe -m slip_reader.run_once
# จำกัดช่วงเวลา (อ่านเฉพาะหลังเวลานี้) — กันอ่านย้อนทั้งหมด:
app\.venv\Scripts\python.exe -m slip_reader.run_once "2026-06-16 00:00:00"
```

**หมายเหตุ path DB:** `run_once.py` ฮาร์ดโค้ด `C:\Users\yklog\YK_LINE_ARCHIVER\line_archive.db`
(path บน server). ถ้ารันบน dev ให้ชี้ DB ของ dev — แก้ตัวแปร `DB` ใน `run_once.py` ชั่วคราว
หรือก๊อป DB มาทดสอบ. **idempotent**: รันซ้ำไม่เกิดรายการซ้ำ (กันด้วย slip_line_message_id).

จากนั้นเปิด `/petty/review` (login หมิว/แอดมิน) → เห็นรายการ AI อ่านมา → อนุมัติ/แก้/ทิ้ง.

---

## 4. Deploy บน server (เมื่อ dry-run + dev นิ่งแล้ว)

slip-reader รันบน server เดียวกับ archiver (มี venv + DB อยู่แล้ว). 2 ทางเลือก:

**(ก) รันเป็นรอบด้วย Scheduled Task** (แนะ — เบา, ไม่ต้อง service ค้าง):
- Task รัน `python -m slip_reader.run_once "<since>"` ทุก ~15–30 นาที (cwd = `ProjectYK_System/`)
- env (`ANTHROPIC_API_KEY`, `YK_SLIP_INGEST_TOKEN`, `MVP_INGEST_URL`) ใส่ใน `.env` แล้วโหลด
  ก่อนรัน หรือใส่เป็น env ของ Task (SYSTEM account).
- เหตุผลรันเป็นรอบ: archiver เก็บข้อความให้ฟรีอยู่แล้ว; อ่านย้อนทั้งวันทีเดียวแม่นพอ ๆ กับ
  ดูสดทุกข้อความ แต่ถูกกว่าหลายเท่า (ดู spec §7 + memory `project-ai-watch-line-group`).

**(ข) NSSM service** (ถ้าอยากให้ทำงานตลอด): ทำ `run_loop.py` ที่วน `run_once` + sleep
แล้วลงเป็น service เหมือน `YKLineBot` (ดู `line_archiver/RUNBOOK`/memory `reference-line-archiver`).
ปัจจุบันยังไม่มี `run_loop.py` — สร้างเมื่อเลือกทางนี้.

**Deploy โค้ด:** ก๊อปโฟลเดอร์ `ProjectYK_System/slip_reader/` ขึ้น server (path เดียวกัน) +
`app/.venv/Scripts/pip install -r slip_reader/requirements.txt` (anthropic, httpx).

---

## 5. กฎเงิน (ห้ามข้าม)

- ยอดมาจาก**สลิปเท่านั้น** — อ่านไม่ได้/ไม่มีสลิป = ไม่สร้าง draft (ไม่เดายอด).
- ทุกรายการเข้า `pending_review` → **คนกด approve เสมอ** (ไม่มี auto-post).
- LCB เท่านั้นเฟสนี้ (`site_code="LCB"` ติดทุกแถว).
- ไม่เขียน Google Sheet (เขาใช้ชีตจริงอยู่ — รอระบบนิ่งค่อยทำ sync เฟสหลัง).

## 6. ตรวจย้อนกลับ

ทุก entry ที่ approved มี `slip_media_path` + `slip_ref_code` ชี้กลับสลิปต้นทางใน archiver,
และ `parsed_payload_json` เก็บผลดิบที่ AI อ่าน — ใช้สอบย้อนได้ว่ายอดมาจากสลิปใบไหน.
