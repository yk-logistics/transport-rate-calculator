---
name: project-pwa-todo-taskbar-icon
description: PWA icon YK น้ำเงิน-เหลืองสำหรับ pin /todo ลง Taskbar — deploy + commit แล้ว 5ก.ค.2026 (542e806); โอต้องลบ shortcut เก่าแล้ว install ใหม่
metadata: 
  node_type: memory
  type: project
  originSessionId: 522ca85b-82a0-4685-9d36-05ea9ce334ba
---

5 ก.ค. 2026 — ทำหน้า app.yklogistics.uk เป็น PWA ติดตั้งได้ (โอขอ icon สวยบน Taskbar สำหรับ /todo):

- `static/icons/` — icon YK พื้นน้ำเงินไล่เฉด อักษรเหลืองทอง (Segoe UI Black) 512/192/apple-touch/favicon; สร้างด้วย PIL supersample 4x (สคริปต์ไม่ได้เก็บ — วาดใหม่ได้จาก spec ใน commit message)
- `static/manifest.webmanifest` — start_url=/todo, display=standalone, theme #1e3a8a
- `static/sw.js` — passthrough ล้วน (จงใจไม่ cache กันไฟล์ค้างหลัง deploy); เสิร์ฟผ่าน route `/sw.js` ที่รากเพื่อ scope `/` + อยู่ใน PUBLIC_PREFIXES (ก่อน login)
- `base.html` — favicon/manifest/apple-touch/theme-color + SW registration ทุกหน้า

Commit `542e806` บน branch fix/slip-trip-fee-kb-display + deploy บน server แล้ว (verify public: sw.js=application/javascript, manifest=application/manifest+json, icons 200 หมด)

**ค้างที่โอ:** ลบ shortcut เก่าออกจาก Taskbar → เปิด https://app.yklogistics.uk/todo ใน Chrome → ⋮ → Cast, save, and share → Install page as app → pin ตัวใหม่

บทเรียน deploy war วันนี้อยู่ใน [[reference-mvp-deploy-restart-gotcha]]
