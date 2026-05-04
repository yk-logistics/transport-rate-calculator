# โฮสต์ทดลองฟรี (พ่อ / คนใน) — FastAPI + PostgreSQL

GitHub Pages **รัน Python ไม่ได้** — ใช้คู่นี้ได้ในโหมดฟรี (ยอมรับว่าเว็บจะ **หลับ** เมื่อไม่มีคนเปิดนาน ๆ ครั้งแรกอาจโหลด ~30–60 วินาที):

| ชิ้นส่วน | บริการฟรีที่แนะนำ | หมายเหตุ |
|----------|-------------------|----------|
| ฐานข้อมูล | [Neon](https://neon.tech) | Postgres จริง, SSL, ลบโปรเจกต์ทิ้งได้เมื่อทดลองจบ |
| แอป | [Render](https://render.com) Web Service `plan: free` | ต่อ GitHub repo นี้, ใช้ `render.yaml` ที่ราก repo |

## 1) สร้างฐานข้อมูล Neon

1. สมัคร Neon → สร้าง Project → สร้าง database  
2. คัดลอก **Connection string** แบบมีรหัสผ่าน (URI)  
3. แปลงให้ SQLAlchemy ใช้ไดรเวอร์ psycopg2 ได้โดย:
   - ถ้าได้ `postgres://...` หรือ `postgresql://...` สคริปต์/แอปจะเติม `+psycopg2` ให้อัตโนมัติ  
4. ถ้า Neon บังคับ SSL: ต่อท้าย `?sslmode=require` (หรือตามที่ Neon บอก)

## 2) ย้ายข้อมูลจากเครื่อง (SQLite) → Neon ครั้งเดียว

### วิธีเร็ว (สคริปต์เดียว)

จากราก repo Project YK (PowerShell):

```powershell
cd "C:\Users\Home\Desktop\Project YK"
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force   # ถ้าโดนบล็อกรันสคริปต์
.\ProjectYK_System\tools\cloud_demo_setup.ps1
```

สคริปต์จะถาม `DATABASE_URL` แล้ว `pip install` + รัน `sqlite_to_postgres.py --wipe` ให้ — จากนั้นพิมพ์รายการ env ให้ไปวางใน Render

### วิธีมือ

บนเครื่องที่มี `ProjectYK_System/app/app.db` (PowerShell):

```powershell
cd "C:\Users\Home\Desktop\Project YK"
.\ProjectYK_System\app\.venv\Scripts\activate   # ถ้าใช้ venv
pip install -r ProjectYK_System\app\requirements.txt
$env:DATABASE_URL="postgresql+psycopg2://USER:PASS@HOST/neondb?sslmode=require"
python ProjectYK_System\tools\sqlite_to_postgres.py --wipe
```

- **`--wipe`** จะ **ลบตารางทั้งหมดบน Postgres เป้าหมาย** แล้วสร้างใหม่ + คัดลอกข้อมูลจาก SQLite — ใช้กับ DB ทดลองเท่านั้น  
- เสร็จแล้วควรเห็นข้อความ `Done: copied all tables...`

## 3) ตั้งค่า Render

**ก่อน:** โค้ดที่มีโฟลเดอร์ `ProjectYK_System/` และไฟล์ `render.yaml` ที่ราก repo ต้องอยู่บน **GitHub** ที่คุณผูกกับ Render (ถ้ายัง push แค่เครื่องคิดเรทอย่างเดียว ต้อง push โปรเจกต์เต็มหรือสร้าง repo ใหม่)

1. New **Web Service** → เชื่อม GitHub repo **Project YK** (หรือ mirror ที่มีโค้ดเต็ม)  
2. Render จะอ่าน `render.yaml` — `rootDir` = `ProjectYK_System/app`  
3. ในแท็บ **Environment** ใส่ตัวแปร:

| Key | ตัวอย่าง |
|-----|----------|
| `DATABASE_URL` | ค่าเดียวกับที่ใช้ย้ายข้อมูล (สตริง Postgres เต็ม) |
| `YK_PREVIEW_AUTH` | `1` |
| `YK_PREVIEW_USER` | เช่น `yk` |
| `YK_PREVIEW_PASSWORD` | รหัสยาวพอสมควร (แชร์ให้พ่อ/คนในเท่านั้น) |

4. Deploy — รอ build เสร็จ แล้วเปิด URL ที่ Render ให้  
5. เบราว์เซอร์จะเด้ง **HTTP Basic** — ใส่ user/password ตามที่ตั้ง

- **`/health`** ไม่บังคับรหัส (ให้ Render / monitor เช็คได้)  
- รูปอัปโหลดคนขับบนเครื่อง **ไม่** ถูกย้ายไป Neon — บนโฮสต์ฟรีไฟล์ local จะหายเมื่อรีสตาร์ท; หน้า Daily/ตารางข้อมูลหลักยังใช้ได้

## 4) ลบข้อมูลทีหลัง

- **Neon**: ลบ branch / project ในแดชบอร์ด Neon  
- **Render**: ลบ Web Service หรือปิด deploy

## 5) ข้อจำกัดฟรีที่ควรรู้

- เว็บหลับ → ครั้งแรกหลังหลับช้า  
- ข้อมูลบนอินเทอร์เน็ต = มีความเสี่ยงรั่ว — ใช้รหัสยาว + อย่าแชร์ URL สาธารณะ + ลบเมื่อทดลองจบ  
- ไม่เหมาะเป็น production จริงจังโดยไม่มีแผน backup / security review

## ไฟล์ที่เกี่ยวข้องใน repo

- `ProjectYK_System/app/db_config.py` — เลือก SQLite / Postgres จาก `DATABASE_URL`  
- `ProjectYK_System/app/preview_auth.py` — Basic auth เมื่อ `YK_PREVIEW_AUTH=1`  
- `ProjectYK_System/tools/sqlite_to_postgres.py` — ย้ายข้อมูล  
- `render.yaml` — ต้นแบบ deploy Render
