---
name: project-mvp-password-db-swap-gotcha
description: DB-only deploy ทับรหัสผ่าน yk1 บนเซิร์ฟเวอร์ — ต้อง preserve appuser ทุกครั้งที่ swap DB
metadata: 
  node_type: memory
  type: project
  originSessionId: afc9f978-5a25-4d9c-9701-35beb33d2e9e
---

2 ก.ค. 2026: โอเข้า MVP ไม่ได้เพราะ DB-only deploy (swap_db) เอา app.db จากเครื่อง Dev ไปทับเซิร์ฟเวอร์ → `appuser.password_hash` ของ yk1 ย้อนกลับเป็นรหัสเก่า (hash local == hash server พิสูจน์แล้ว) รหัสที่โอเปลี่ยนบนเซิร์ฟเวอร์หายไป

แก้ไข: reset yk1 = รหัสชั่วคราว `YKtemp2026!` + `must_change_pw=1` (โอตั้งรหัสใหม่เองตอนล็อกอิน) — ลำดับ: Stop-ScheduledTask YK_MVP_APP → UPDATE hash ใน DB → Start task → verify POST /login = 303→/account/password

**Why:** appuser table อยู่ใน app.db เดียวกับข้อมูลเงิน — swap ทั้งไฟล์ = swap รหัสผ่านด้วย

**How to apply:** ทุกครั้งที่ deploy แบบ `--with-db` / swap_db.ps1: **ก่อน swap ให้ SELECT password_hash+must_change_pw ของ appuser ทุกแถวจาก DB เซิร์ฟเวอร์ แล้ว UPDATE กลับหลัง swap** (หรือใส่ขั้นตอนนี้ลง swap_db.ps1 เลย) ไม่งั้นโอโดนล็อกเอาต์ทุกรอบ deploy; login_guard ล็อก 15 นาทีเป็น in-memory — restart แอปล้างได้; ดู [[reference-mvp-server-deploy]]
