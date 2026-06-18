# Design — แอปสรุปคลิป YouTube เป็นไทย (เว็บ localhost)

วันที่: 2026-06-18
สถานะ: รอ โอ รีวิว

## เป้าหมาย

หน้าเว็บเล็กๆ รันบนเครื่องโอ ที่ใส่ URL คลิป YouTube → เลือก model → ได้สรุปภาษาไทย
ต่อยอดจากเครื่องมือ CLI ที่ทำงานแล้ว (`_Claude Tools/yt-summarize/`) โดยไม่แตะ Project YK
(payroll/app.db ไม่เกี่ยว)

## ขอบเขต (ตกลงกับโอแล้ว)

- รันที่ **localhost** บนเครื่องโอ คนเดียวใช้ — ไม่ขึ้นเน็ต, ไม่มี login/RBAC
- รองรับ **หลาย URL ในครั้งเดียว** (batch) และ **ทีละคลิป**
- **สรุปเป็นไทยเสมอ** (คลิป Eng ก็แปลสรุปเป็นไทย)
- **เลือก model ได้** จาก dropdown: Qwen (ฟรี), Gemini, Claude, DeepSeek + บอกวิธีเพิ่มเจ้าอื่น
- เก็บ **ประวัติ** + ดูย้อนหลัง + **ถามต่อ (chat)** เกี่ยวกับคลิปนั้น
- chat ใช้ **model เดียวกับที่เลือกตอนสรุป** (ยืนยันแล้ว)
- เฟสแรกทำ **Qwen ให้เสร็จก่อน** (มี key พร้อม) แล้ววางช่องเติม key เจ้าอื่นทีหลัง — ไม่รอ key ครบ (ยืนยันแล้ว)

## สถาปัตยกรรม

โฟลเดอร์ `_Claude Tools/yt-summarize/` (แยกจาก Project YK):

```
yt-summarize/
  get_transcript.py   — (มีแล้ว) ดึงซับ + แปลง vtt→text. reuse.
  yt_summary.py       — (มีแล้ว) CLI เดิม. คงไว้ใช้สาย command line.
  providers.py        — ใหม่: ตัวกลางคุยทุก model. summarize(text, model_key) -> str
  web/
    main.py           — ใหม่: FastAPI app, port 8030
    store.py          — ใหม่: อ่าน/เขียนประวัติเป็น JSON (ไม่มี DB)
    templates/
      index.html      — หน้าเดียว (Jinja2 + HTMX + Tailwind CDN, ตาม stack YK)
      _result.html    — partial สำหรับ render ผลสรุป (HTMX swap)
  out/
    history.json      — ประวัติการสรุปทั้งหมด
    <vid>.summary.th.md — ไฟล์สรุป (คงรูปแบบเดิม)
  start_web.bat       — ใหม่: เปิด venv + รันแอป + เปิด browser
```

stack: FastAPI + Jinja2 + HTMX + Tailwind CDN — เหมือน Project YK ไม่มี Node build.

## ส่วนประกอบ (แต่ละหน่วยหน้าที่เดียว)

### providers.py — ตัวกลาง model
หน้าที่เดียว: รับ (ข้อความ, model_key) คืนสรุปไทย. ซ่อนความต่างของแต่ละเจ้าไว้ในนี้.

```
PROVIDERS = {
  "qwen":     { label, kind="qwen_ps1",  key_file=None },          # ฟรี พร้อม
  "gemini":   { label, kind="rest", key_file="gemini.key", ... },
  "claude":   { label, kind="rest", key_file="claude.key", ... },
  "deepseek": { label, kind="rest", key_file="deepseek.key", ... },
}

def available() -> list   # โมเดลที่มี key ครบ (qwen เสมอ)
def summarize(text, model_key) -> str
def chat(transcript, prior_summary, question, model_key) -> str
```

- `kind="qwen_ps1"` → เรียก qwen.ps1 ผ่านไฟล์ชั่วคราว (เหมือน yt_summary.py ที่ทำแล้ว)
- `kind="rest"` → HTTP POST ไป endpoint ของเจ้านั้น (อ่าน key จาก *.key)
- เจ้าที่ไม่มี key → ไม่อยู่ใน `available()`; dropdown โชว์ disabled + ข้อความ "ใส่ key ที่ settings"
- prompt สรุป/chat reuse จาก yt_summary.py (ภาษาไทย)

### web/store.py — ประวัติ
JSON list ใน `out/history.json`. แต่ละ entry:
```
{ id, url, video_id, model, created_at, transcript_path, summary_md, chat: [{q, a, ts}] }
```
ฟังก์ชัน: `add_summary(...)`, `get(id)`, `list_recent(n)`, `add_chat(id, q, a)`.
UTF-8 ไม่มี BOM (กฎเครื่องนี้).

### web/main.py — FastAPI (port 8030)
- `GET  /`            → index.html (ฟอร์ม + ประวัติ + dropdown model จาก providers.available())
- `POST /summarize`   → รับ urls[] + model → ดึง transcript → providers.summarize → store → คืน _result.html (HTMX)
- `POST /ask`         → รับ id + question → providers.chat → store.add_chat → คืน partial
- `GET  /history/{id}`→ คืนสรุปเดิม render
- `GET  /settings`    → หน้าวาง API key (เขียนลง *.key)  [เฟสแรกแบบง่าย: textarea ต่อเจ้า]
- bind **127.0.0.1** เท่านั้น (ไม่ใช่ 0.0.0.0) — กัน key รั่วออก LAN

## Data flow

สรุป: `URL → get_transcript → providers.summarize(model) → store.add_summary → render`
chat:  `id → load transcript+summary → providers.chat(question) → store.add_chat → render`
batch: วน urls ทีละอัน, อันไหน NO_SUBTITLES ก็ข้ามและรายงานในผล

## Error handling

- ไม่มีซับ → แสดง "คลิปนี้ไม่มีซับ สรุปไม่ได้" (ไม่ crash ทั้ง batch)
- model ไม่มี key → ก่อนกดสรุปไม่ให้เลือก; ถ้าหลุดมา → ข้อความบอกไป settings
- คลิปยาวเกิน → ตัดที่ ~280k ตัวอักษร + เตือนบนผล (ตามที่ CLI ทำ)
- REST API error (rate limit/401) → โชว์ error ของเจ้านั้นตรงๆ ไม่กลืน

## Testing / ตรวจรับ

- รัน `start_web.bat` → เปิด localhost:8030 ได้
- ใส่คลิป Eng 1 อัน + เลือก Qwen → ได้สรุปไทย (เทียบกับ CLI ที่พิสูจน์แล้ว)
- ใส่ 2 URL → ได้ 2 สรุป, อันที่ไม่มีซับขึ้น error เฉพาะอันนั้น
- กดถามต่อ → ได้คำตอบไทย ต่อใน history
- ปิดเปิดแอปใหม่ → ประวัติยังอยู่ (history.json)
- dropdown โชว์ Qwen ใช้ได้, เจ้าอื่นขึ้น "ต้องใส่ key"

## YAGNI — ไม่ทำในเฟสนี้

- ไม่มี login/RBAC, ไม่มี DB, ไม่ขึ้น server
- ไม่ถอดเสียงคลิปที่ไม่มีซับ (ต้องโหลด audio + STT — เฟสหลังถ้าต้องการ)
- ไม่ทำ user หลายคน / ไม่ทำ usage/cost meter (เฟสหลังถ้าจ่ายเงินเยอะ)

## วิธีเพิ่ม model เจ้าใหม่ (เช่น เจ้าอื่นในอนาคต)

1. วาง key ไฟล์ `_Claude Tools/<ชื่อ>.key`
2. เพิ่ม entry ใน `PROVIDERS` (label + endpoint + รูปแบบ payload)
3. ไม่ต้องแตะ main.py/หน้าเว็บ — dropdown อ่านจาก providers.available() อัตโนมัติ
