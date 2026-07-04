---
name: project-merge-daily-grid
description: "Daily + Daily Grid pages merged into one at /daily, deployed live 2026-06-24"
metadata: 
  node_type: memory
  type: project
  originSessionId: 1dd0964b-b7b3-4662-8d3c-43343839f8b5
---

ยุบหน้า Daily (list) + Daily Grid เป็นหน้าเดียวที่ `/daily` เพื่อลดความสับสน (โอขอ) — รวมฟีเจอร์ครบ ไม่ตัด.

- `/daily` เสิร์ฟ `daily_grid.html` (AJAX, แก้แบบ Excel, Ctrl+Enter, ตัวกรองค่าว่าง AD/U).
- `/daily/grid` → redirect 301 ไป `/daily` พร้อม query string (bookmark/preset เก่าใช้ได้).
- ยกคอลัมน์ชื่อจริง driver_name/plate_no/tail_plate/customer_name จาก list เดิมเข้ามา (read-only, ซ่อน default); `/api/daily/grid-data` ส่งค่าเพิ่มผ่าน master maps.
- ช่องค้นใช้ `q` รวมอย่างเดียว; localStorage รวมเป็น `yk_daily_hidden_v1`; ลบ `daily_list.html`.
- **ไม่แตะ** `/api/daily/grid-save`.

Spec: `docs/superpowers/specs/2026-06-24-merge-daily-and-daily-grid-design.md`.
Merged to main + **deployed live** to app.yklogistics.uk (verified new code on server by file markers, port 8010 up, /login 200). ลบ daily_list.html ค้างบน server แล้ว (copy-deploy ไม่ลบไฟล์เก่าเอง — ดู [[reference-mvp-deploy-restart-gotcha]]).

Known: `test_check_link_menu` fails แต่เป็น pre-existing (ตรวจด้วย git stash แล้ว) ไม่เกี่ยวงานนี้.
