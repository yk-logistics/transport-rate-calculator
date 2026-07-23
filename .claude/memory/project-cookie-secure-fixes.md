---
name: project-cookie-secure-fixes
description: "8ก.ค. แก้ cookie ขาด Secure flag 2 จุด (driver session + oauth_state) — prod เป็น HTTPS ผ่าน Cloudflare ควร Secure; driver deploy แล้ว, oauth รอ deploy พร้อมยาง v48"
metadata: 
  node_type: memory
  type: project
  originSessionId: cc086771-bff3-4262-a48c-795610894992
---

**8 ก.ค. 2026 — self-review เจอ cookie 2 จุดขาด `secure=` flag** (prod = HTTPS ผ่าน Cloudflare tunnel → ควรมี Secure ทุก cookie). แก้ทั้งคู่ด้วย TDD (test แดงก่อน→เขียว→พิสูจน์ revert แดง):

1. **driver session cookie** (`services/driver_auth.py:170` `set_session_cookie`) — เดิม hardcode `secure=False # TODO`. บัตรผ่านถาวรคนขับ PWA = ร้ายแรงสุด. แก้: `secure=os.environ.get("YK_INSECURE_COOKIES","").lower() not in ("1","true","yes")` (gate เดียวกับ main.py:734).
   → **DEPLOY แล้ว** commit 8e6b709 (scp surgical + restart YK_MVP_APP + verify HEALTH/DRIVER_LOGIN=200); backup บน server = `driver_auth.py.bak_before_secure_fix`

2. **oauth_state cookie** (`main.py:2537` email_oauth_start) — Gmail sync CSRF guard, ค่าสุ่ม 10 นาที ใช้นานๆครั้ง = เสี่ยงต่ำ. แก้: `secure=_secure_cookies` (module var).
   → **โค้ดเข้า HEAD แล้ว** (ถูกลากไปกับ commit ยาง 43a8a57 โดยบังเอิญ เพราะแก้ค้าง working tree ตอน session ยาง commit); test แยก commit 18080d2
   → **DEPLOY LIVE แล้ว** 8ก.ค. — ขึ้นพร้อม deploy ระบบยาง v48 (server schema=48); verified บน server: บรรทัด `samesite="lax", secure=_secure_cookies)` + HEALTH 200 + tire endpoint 303. **ครบทั้ง 2 จุด ทุก cookie มี Secure บน HTTPS แล้ว**

**gotcha ที่เจอ:** `_secure_cookies` (main.py:734) freeze ตอน import → test ต้อง `monkeypatch.setattr(main,"_secure_cookies",...)` ไม่ใช่ setenv (ต่างจาก driver_auth ที่อ่าน env สดทุก call). ดู [[project-app-has-test-suite]] เรื่องรัน test.

**ท่า deploy ผ่าน Tailscale (Windows server, shell=PowerShell):** ssh inline quote ซ้อนพัง ($ หาย) → เขียน .ps1 scp ไปรัน `powershell -ExecutionPolicy Bypass -File`; copy บน server ใช้ `Copy-Item` ไม่ใช่ `copy`. ดู [[reference-deploy-via-tailscale]] [[reference-mvp-server-deploy]]
