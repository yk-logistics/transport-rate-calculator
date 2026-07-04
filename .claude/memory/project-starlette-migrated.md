---
name: project-starlette-migrated
description: "4ก.ค. 2026: อัป fastapi 0.139/starlette 1.3.1 บน server+dev แล้ว (ปิด CVE ครบ) — pin เก่าปลด; route ใหม่ต้องใช้ TemplateResponse(request, name, ctx)"
metadata: 
  node_type: memory
  type: project
  originSessionId: d4a29959-9dce-4e25-82a7-9d031c3c20be
---

Migration fastapi/starlette เสร็จ 4 ก.ค. 2026 เย็น (จาก finding S5):

- **ตอนนี้:** fastapi 0.139.0 + starlette 1.3.1 ทั้ง server (`YK_MVP\app\.venv`) และ dev venv; pip-audit runtime = 0 CVE; pytest อัปเป็น 9.x (dev-only)
- **วิธีที่ใช้ (2 จังหวะ เสี่ยงต่ำ):** (A) rewrite `templates.TemplateResponse("x.html", ctx)` → `(request, "x.html", ctx)` ทั้ง 130 จุดใน main.py (regex + AST ยืนยัน request ใน scope) — signature ใหม่ใช้ได้ตั้งแต่ starlette 0.29 จึง**เข้ากันได้สองทาง** → เทสต์ 428 ผ่านทั้งสอง stack → deploy โค้ดก่อนโดย server ยังรันเวอร์ชันเดิม (B) ค่อย pip อัป → restart → verify (login render + health + log ไม่มี error)
- **กติกาจากนี้:** route ใหม่**ต้อง** `templates.TemplateResponse(request, "x.html", ctx)` — แบบเก่า (ชื่อไฟล์ขึ้นก่อน) พังทันทีบน starlette 1.x (`TypeError: unhashable type: 'dict'` ใน jinja2 cache); CLAUDE.md หัวข้อ Version pins อัปเดตแล้ว
- **เก็บครบแล้ว (เย็นวันเดียวกัน):** on_event → lifespan แล้ว (deprecated ตัวสุดท้ายหมด) + แก้ db_config ให้ is_sqlite ดูจาก scheme จริง (เดิม DATABASE_URL sqlite โดนเหมาเป็น postgres — เทสต์ทุกไฟล์ได้ engine ตรง prod ขึ้น); uvicorn คง 0.34

**Why:** starlette 0.38.6 มี CVE 6 รายการ (รวม multipart DoS ที่จุด pre-auth /login) ติด pin มาแต่เมษา

**How to apply:** ถ้า route ใหม่ render หน้าไม่ขึ้นด้วย TypeError unhashable ให้เช็ค signature ก่อนเลย; รายละเอียดเต็ม `docs/STARLETTE_MIGRATION_NOTES.md` ดู [[project-jul4-day-run]]
