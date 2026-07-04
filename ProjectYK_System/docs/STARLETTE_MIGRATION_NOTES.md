# ✅ ทำแล้ว 4 ก.ค. 2026 (เย็น) — อัป fastapi 0.139.0 / starlette 1.3.1 ปิด CVE ครบ

**ผลจริง:** ทำแบบ 2 จังหวะ — (A) rewrite TemplateResponse 130 จุดเป็น signature ใหม่
(เข้ากันได้ทั้ง 0.38.6/1.3.1 — starlette 0.29+ รับแบบใหม่แล้ว) + AST ยืนยัน request ใน scope ครบ
→ เทสต์ 428 ผ่าน**ทั้งสอง stack** → deploy โค้ดก่อน (server ยังเวอร์ชันเดิม = เสี่ยงศูนย์);
(B) pip อัป server+dev → restart → /login render จริง + /health + ไม่มี error ใน log;
pip-audit เหลือศูนย์ CVE runtime (pytest dev-only อัปเป็น 9.x แล้วด้วย); uvicorn คง 0.34 (ไม่จำเป็นต้องอัป);
`@app.on_event("startup")` ยัง deprecated-but-working บน fastapi 0.139 — ค่อยย้ายเข้า lifespan เมื่อสะดวก
**กติกาโค้ดใหม่:** route ใหม่ต้องเรียก `templates.TemplateResponse(request, "x.html", ctx)` เสมอ

---

# (แผนเดิม — เก็บไว้อ้างอิง) อัป fastapi/starlette หลุด pin (ปิด CVE ชุด starlette 0.38.6)

> ที่มา: S5 รอบแรก 4 ก.ค. 2026 — pip-audit เจอ starlette 0.38.6 มี CVE 6 รายการ
> (รวม CVE-2024-47874 multipart DoS — จุดรับ pre-auth คือฟอร์ม /login) แต่ติด pin
> `fastapi<0.115, starlette<0.40`; python-multipart อุดแล้ว (0.0.32, 4 ก.ค.)
> ความเสี่ยงระหว่างรอ: มี Cloudflare + login_guard คั่นอยู่ — ไม่ฉุกเฉิน แต่ควรทำใน ก.ค.

## ผล recon จริง (4 ก.ค. — venv ทิ้งขว้าง fastapi 0.139.0 + starlette 1.3.1, Python 3.12)

รันเทสต์ทั้งชุด 424 ตัว: **203 ผ่าน / 52 fail / 169 error — ทุกตัวที่พังมาจากสาเหตุเดียว**:
starlette 1.x เปลี่ยน signature `Jinja2Templates.TemplateResponse` จาก
`(name, context)` เป็น `(request, name, context)` → ของเราเรียกแบบเก่า **129 จุด
(main.py ไฟล์เดียว)** อาการคือ `TypeError: unhashable type: 'dict'` ใน jinja2 cache
(ชื่อ template กลายเป็น request ไป)

ที่ **ไม่พัง**: bcrypt 5 / sqlmodel 0.0.39 / httpx TestClient / login_guard / payroll API
(เทสต์ API ล้วนผ่านหมด) — Jinja2 filters (`dmy` ฯลฯ) ผูกกับ `templates.env` ไม่กระทบ

## ขั้นตอน migration (งาน mechanical — Sonnet ทำได้ตามนี้)

1. เปิด branch แยก เช่น `feat/starlette-1x` (ห้ามทำบน branch ที่มีงานสลิปค้าง working tree)
2. แก้ 129 จุดใน `app/main.py`:
   - รูปแบบ: `templates.TemplateResponse("x.html", ctx)` → `templates.TemplateResponse(request, "x.html", ctx)`
   - ทุก call site มี `request: Request` ใน scope อยู่แล้ว (ctx มาจาก `base_context(request)`)
   - จุดที่ ctx สร้าง inline ไม่ผ่าน base_context ให้เช็คว่ามี request — ถ้าไม่มีใช้ `ctx["request"]`
3. แก้ deprecated `@app.on_event("startup")` (main.py:702) → รวมเข้า lifespan ที่มีอยู่
4. `requirements.txt`: ปลด pin →
   `fastapi>=0.139,<1` / `starlette>=1.3,<2` / `uvicorn[standard]>=0.50,<1` + ลบ comment pin เก่าหัวไฟล์
5. รันเทสต์เต็ม: `.venv-ใหม่\Scripts\python -m pytest tests/ -q` ต้อง **424 ผ่านหมด**
6. เช็คหน้าจริงบนเครื่อง dev อย่างน้อย: `/` `/daily` grid, `/payroll` สลิป 1 ใบ (PDF ไทย), `/admin/server-health`, `/line`
7. **Deploy = ชุดเดียวห้ามแยก** (โค้ดใหม่รันกับ starlette เก่าไม่ได้ และกลับกัน):
   - นอกเวลางาน + แจ้งโอ; สำรอง `YK_MVP\app\app.db` ก่อน (มี nightly อยู่แล้ว)
   - server: `pip install -U fastapi starlette uvicorn[standard]` ใน `.venv` → scp `main.py`+`requirements.txt` → restart `YK_MVP_APP`
   - ตรวจ: `/health` schema ok, `/login` 200, เปิด `/daily` จริง 1 หน้า
   - rollback: pip install เวอร์ชันเดิมตาม requirements เก่า + scp main.py เดิม (git มีครบ)

## ระวัง

- **อย่า scp main.py เวอร์ชันใหม่ไป server ก่อนอัป starlette บน server** — จุดนี้คือเหตุที่ยังไม่ทำวันนี้ (4 ก.ค. บ่ายวันศุกร์ ทีมใช้งานอยู่)
- pytest CVE (dev-only) อัปได้พร้อมกัน: `pip install -U pytest`
- หลังผ่าน ให้ลบหมายเหตุ pin ใน `CLAUDE.md` (หัวข้อ Version pins) ด้วย
