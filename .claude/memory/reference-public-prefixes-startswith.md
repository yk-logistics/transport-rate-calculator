---
name: reference-public-prefixes-startswith
description: "RBAC PUBLIC_PREFIXES ใน main.py จับแบบ startswith ไม่มี slash — route ใหม่ห้ามขึ้นต้นด้วย /driver, /check, /health ฯลฯ ไม่งั้นหลุด auth ทั้งหน้า"
metadata: 
  node_type: memory
  type: reference
  originSessionId: fd0894dd-f24f-402b-bcc2-26a58006d9bf
---

`RbacMiddleware` ใน `ProjectYK_System/app/main.py` ข้าม auth ให้ทุก path ที่
`startswith` ค่าใน `PUBLIC_PREFIXES` — หลายตัว**ไม่มี slash ปิดท้าย** เช่น
`"/driver"`, `"/check"`, `"/health"`, `"/sw.js"`, `"/login"`, `"/logout"`.

**Why:** 14ก.ค. ทำหน้า `/driver-income` แล้วพบว่า "/driver-income".startswith("/driver")
= จริง → หน้าเงินหลุด RBAC เป็นหน้าสาธารณะเงียบๆ (เทสต์ viewer ได้ 404 แทน 403 คือเบาะแส)

**How to apply:** ตั้งชื่อ route ใหม่ให้เลี่ยง prefix พวกนี้ (เคสจริงใช้ `/income/drivers` แทน)
และใส่เทสต์ "ไม่ล็อกอิน → 303 /login" ทุกครั้งที่เพิ่มหน้าใหม่นอกเมนูเดิม
(ดู tests/test_driver_income.py::test_requires_login_not_public เป็นแบบ)
