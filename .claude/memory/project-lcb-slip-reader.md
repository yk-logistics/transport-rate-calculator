---
name: project-lcb-slip-reader
description: "LCB petty-cash AI slip-reader — read LINE transfer slips → draft → human approve in MVP. Proof done, code merged, awaiting API key for live dry-run."
metadata: 
  node_type: memory
  type: project
  originSessionId: cd7cfc63-f3e1-4bb3-ae9b-b71a8f1c9665
---

เป้าหมาย: ลดงานมือของหมิว — "โอนเงินเสร็จต้องมานั่งลงชีตสดย่อย LCB". ให้ AI อ่านสลิปโอนจาก
กลุ่ม LINE "Y.K. หัวลาก LCB" (เก็บใน archiver) → ร่างรายการ (คน/ยอด/งาน) → คนกดอนุมัติในเว็บ MVP.

**สถานะ (2026-06-19): โค้ด merge เข้า `main` แล้ว** (merge `aef1916`). เหลือ live dry-run ที่รอ API key.

**พิสูจน์ความแม่นแล้ว (เฟส 1):** อ่านสลิป SCB จริง 13 ใบ = ยอด/คนขับ/งาน/เวลา ครบ 100%.
ค้นพบ: สลิปมี "บันทึกช่วยจำ" ที่หมิวพิมพ์เอง (เช่น "วิโรจน์ รับตู้ดรอป") → สลิปใบเดียวบอกครบ,
ข้อความ LINE เป็นแค่ตัวยืนยัน. รูปในกลุ่มไม่ใช่สลิปทั้งหมด (มีใบงาน/แพลน/ตารางสรุปรายคนปนมา → ต้องคัด).
ชีตกับ LINE ไม่ตรง 1:1 (ชีตลงตามวันจ่าย+รวม 1 แถว/งาน) → AI ควร "อ่านสลิปเป็นรายการให้คนอนุมัติ"
ไม่ใช่ "เดาว่าลงแถวไหน". รายงานเต็ม: `reports/lcb_petty_ai_accuracy_2026-06-18.md`.

**โครงสร้าง (เฟส 2 ที่สร้างแล้ว):**
- MVP (`app/`): schema v20 (status `pending_review` + คอลัมน์ `slip_line_message_id/slip_media_path/slip_ref_code` บน PettyCashTxn); endpoint `POST /api/petty/ingest` (service-token `YK_SLIP_INGEST_TOKEN`, idempotent by slip msg id, exempt จาก RBAC ใน PUBLIC_PREFIXES); หน้า `GET /petty/review` + approve/reject (admin/office, map เข้า menu "petty").
- service ใหม่ `ProjectYK_System/slip_reader/`: `engine.py` (Claude Haiku 4.5, structured output `output_config.format`, จัดการ refusal, สลับ engine ได้ผ่าน `SLIP_ENGINE`), `plan_context.py` (parse แพลนงานช่วยเติม note/ยืนยันคน), `entry_builder.py` (อ่าน→payload, ไม่มี amount=ไม่สร้าง), `slip_source.py`/`mvp_push.py`/`run_once.py` (pipeline), `dry_run_report.py`.
- 20 เทสต์ผ่าน (12 slip_reader + 8 petty). venv ของ app ลง anthropic 0.109.2 + httpx แล้ว.

**สถานะ deploy (2026-06-24): infra ขึ้น server แล้ว — เหลือแค่โอใส่ secret เอง.**
โอเลือกข้าม dev-test ไป deploy บน server เลย. ที่ Claude ทำเสร็จ (ไม่แตะ key):
- ก๊อป `slip_reader/` (14 ไฟล์ runtime, ไม่เอา tests/_devdata) → `C:\Users\yklog\YK_MVP\slip_reader\` (รันด้วย MVP venv `app\.venv`, มี anthropic+httpx อยู่แล้ว — import ผ่าน).
- สร้างไฟล์ใหม่ในรีโป: `slip_reader/.env.example` (template ไม่มี secret) + `slip_reader/run_slip_reader.bat` (launcher: โหลด .env → run_once ช่วง 2 วันล่าสุด). แก้ `.gitignore` ให้ commit `.env.example` ได้ (`.env` จริงยัง ignore). **ยังไม่ commit** (อยู่ main, รอโอ).
- สร้าง Scheduled Task `YK_SLIP_READER` (SYSTEM, ทุก 20 นาที, รัน run_slip_reader.bat) บน server — Ready แล้ว แต่จะ error ทุกรอบจนกว่าจะมี `.env`.
**MVP บน server = Scheduled Task `YK_MVP_APP` (SYSTEM, at-startup, รัน `start_mvp.bat`) — ไม่ใช่ NSSM** (RUNBOOK §2 ที่พูดถึง nssm ใช้ไม่ได้). ตอนนี้ MVP ยังไม่มี `YK_SLIP_INGEST_TOKEN` → endpoint ตอบ 401.

**เหลือ (โอทำเองในเทอร์มินัลตัวเอง — custody กฎ key):**
1. เพิ่มบรรทัด `set YK_SLIP_INGEST_TOKEN=<สุ่ม>` ใน `C:\Users\yklog\YK_MVP\start_mvp.bat` → restart `YK_MVP_APP` (ระวัง [[reference-mvp-deploy-restart-gotcha]]: kill main.py by path).
2. `Copy-Item slip_reader\.env.example .env` แล้วเติม `ANTHROPIC_API_KEY` + token เดียวกับข้อ 1.
3. รัน `run_slip_reader.bat` มือ 1 รอบ → เปิด `app.yklogistics.uk/petty/review` เช็ครายการ pending_review.

**UPDATE 2026-06-24 (LIVE แล้ว):** โอใส่ key ในเครื่องตัวเอง (ไฟล์ temp) → Claude scp ขึ้น server เขียนลง `.env` (key ไม่โผล่แชต) → ลบไฟล์ temp ทั้ง 2 ที่. token สุ่มเอง จัดการให้หมด: ใส่ใน start_mvp.bat (backup `.bak_before_slip_token`) + restart MVP (kill 2 stale main.py by path) → endpoint ทดสอบผ่าน (good token=400, bad=401). **รันจริง 1 รอบสำเร็จ: PUSHED 54 of 78** (ids 68–121 เป็น pending_review, skip non-slip 24). OCR ยอด+ชื่อแม่น. Task `YK_SLIP_READER` วิ่งทุก 20 นาทีเอง.
**บั๊กค้าง (ไม่ใช่เรื่องเงิน แต่ควรแก้):** `entry_builder.py:34` `first = name.split()[0]` → ดึงคำนำหน้า "นาย" มาเป็น requester แทนชื่อจริง เมื่อ fuzzy match กับ plan roster ไม่เจอ (21/54 แถวขึ้น requester="นาย"). payload เก็บชื่อเต็มถูกต้อง (`recipient_name`). ฟิกซ์ = strip คำนำหน้า (นาย/นาง/น.ส./นางสาว) ก่อน `.split()[0]`. รอโอเคาะก่อนแก้ (logic แตะเงิน).

**UPDATE 2026-06-24 รอบ 2 — เพิ่มสวิตช์ เปิด/ปิด ผ่าน MVP (commit `77110d9`):**
โอบอกยังไม่อยากให้อ่านจริง (กลัวเสียเงินช่วงทดสอบ) → อยากคุมจากหน้าเว็บ. ทำเสร็จ + deploy + เทสต์:
- ตาราง `AppSetting` (key/value, SCHEMA_VERSION 22→23). helper `get_setting/set_setting` ใน main.py.
- service endpoint `GET /api/petty/slip-config` (+`/report`) token-gated → reader ถามก่อนทำงาน. ปิด=ไม่เรียก API เลย (เทสต์ server: พิมพ์ `DISABLED` ออกมา ไม่สร้างแถว ไม่เสียเงิน). reader unreachable→ถือว่าปิด (fail-safe).
- หน้า `GET /petty/slip-control` (admin/office ผ่าน petty menu): สวิตช์เปิด/ปิด + ช่อง "อ่านย้อนตั้งแต่วันที่" (เว้นว่าง=ต่อจากเดิม) + ปุ่ม "เช็คเดี๋ยวนี้" (ตั้ง run_now flag, reader ack ครั้งเดียว) + สถานะ. nav link 🤖 อ่านสลิป.
- reader: `mvp_config.py` (fetch/report) + `run_once.main()` gate ก่อนสร้าง engine. config since-date ชนะ arg.
- เทสต์: +4 reader-gate (engine.read ไม่รันตอนปิด — พิสูจน์ไม่เสียเงิน) +6 MVP. รวม 31 ผ่าน.
- **ค่าเริ่มต้น = ปิด (enabled=0)** บน server แล้ว. schema 23 LIVE. spec: `docs/superpowers/specs/2026-06-24-slip-reader-mvp-control-design.md`.
- **⚠️ git incident:** มี automated process สลับ branch ไป `feat/check-vehicle-edit-trailer` + cherry-pick งานอื่น + revert working-tree กลางคัน → ไฟล์ local ผมโดน revert ชั่วคราว. **commit `77110d9` ครบถ้วน** อยู่บน branch `feat/lcb-daily-fuel-crosscheck` (กู้คืน working-tree จาก commit นี้แล้ว). server มีโค้ดถูกต้อง (scp ก่อน revert). ยังไม่ merge เข้า main.

กฎเงิน: ยอดมาจากสลิปเท่านั้น · คนอนุมัติทุกรายการ (ไม่ auto-post) · LCB ที่เดียว · **ยังไม่แตะ Google Sheet**
(หมิวใช้ชีตจริงอยู่ — รอระบบนิ่งค่อยทำ sync). spec: `docs/superpowers/specs/2026-06-18-lcb-slip-reader-review-design.md`.
เกี่ยวข้อง: [[reference-line-archiver]] (แหล่งสลิป), [[project-ai-watch-line-group]] (ทำไมอ่านเป็นรอบ),
[[reference-server-no-gpu-llm]] (ห้าม self-host LLM), [[project-daily-lcb-sheet]] (ชีตปลายทางเฟสหลัง).
