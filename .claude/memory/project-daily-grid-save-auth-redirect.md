---
name: project-daily-grid-save-auth-redirect
description: "Daily grid Save (and full-edit) \"doesn't persist\" root cause = expired/absent session → POST redirected to /login, frontend res.json() chokes on login HTML"
metadata: 
  node_type: memory
  type: project
  originSessionId: 88db0e66-531a-4800-8509-a9c2e30dcb98
---

โอรายงาน 30มิ.ย.: แก้เดลี่ในระบบ MVP ไม่อัปเดต — กด Save Grid ไม่ติด, F5 ก็ข้อมูลเดิม, "แก้เต็ม" ก็เหมือนเดิม.

**สำคัญ — มี 2 บั๊กแยกกัน:**

**(A) บั๊กจริงที่โอเห็น:** กด Save Grid ขึ้น **"ไม่มีข้อมูลที่แก้ไข"** = `dirtyRows.size===0` (daily_grid.html line ~891). แปลว่า edit ของโอ **ไม่ถูกจับเป็น dirty** → ไม่ส่งอะไรไป server เลย. ไม่ใช่บั๊กฝั่งเซฟ. (กำลังหาเหตุที่ cellEdited ไม่ fire / editor ไม่ commit).

**(B) บั๊ก latent คนละตัว (เจอตอน repro แต่ไม่ใช่อาการของโอ):** ถ้า session หมดอายุ → POST โดน RbacMiddleware redirect 303 /login → frontend `res.json()` เจอ HTML login → throw. session max_age=8h, cookie https_only+same_site=lax. ควรแก้พร้อมกัน (api ตอบ 401 JSON).

**Repro (scratchpad, TestClient + DB copy):**
- NO-AUTH: POST grid-save → 303 /login, **DB ไม่เปลี่ยน**
- AUTHED (patch auth.current_user): → 200 JSON `{ok,updated:1}`, **DB เปลี่ยนจริง** (remark+revenue)

**FIXED+DEPLOYED 30มิ.ย. (commit dad0cf9, live app.yklogistics.uk) — daily_grid.html + main.py + test_rbac_middleware.py:**
1. `commitOpenEditor()` — กด Save → blur ช่องที่ activeElement อยู่ใน .tabulator-cell + รอ 1 tick ให้ cellEdited commit ก่อนเช็ก dirtyRows.size (แก้บั๊ก A หลัก)
2. fetch save: `redirect:"manual"` + ถ้า opaqueredirect/401/403/3xx/ไม่ใช่ JSON → ขึ้น "เซสชันหมดอายุ ล็อกอินใหม่" + ลิงก์ /login, คง dirtyRows (แก้บั๊ก B)
3. RbacMiddleware: `path.startswith("/api/")` + user None → 401 JSON `{error:auth_required}` แทน 303 redirect HTML
4. grid UX (โอขอ): paginationSize 100→1000, height 70→75vh, selector [100,200,400,1000,true]. **footer = bottomCalc สรุป filtered-set (native, recalc on filter/edit)** — ที่ 1000/page = "แถวที่เห็น" สำหรับ view ปกติ; ไม่ทำ per-page calc (สู้ virtual renderer ไม่คุ้ม)
5. **freeze (รอบ 2, a11b643): โอหมายถึง freeze คอลัมน์ซ้าย ไม่ใช่หัวตาราง** — เลื่อนขวาแล้วยังเห็น วันที่/คนขับ/ทะเบียน (แบบ Excel Freeze Panes). FROZEN_FIELDS=[work_date,driver_name,plate_no]. **freeze header แยกต่างหาก = Tabulator ทำเองจาก height (sticky)**
6. **GOTCHA (รอบ 3, 77b8b61): frozen ทับซ้อนตอน scroll!** สมมติฐานเดิม "Tabulator auto-collect ได้" **ผิด** (โอส่ง screenshot ทับซ้อน) — frozen-left ต้อง **contiguous หน้าสุด**; ของเดิม id/site_code/driver_id แทรกกลาง work_date↔driver_name↔plate_no → คอลัมน์อื่นมุดใต้ frozen เวลาเลื่อน. แก้: hoist FROZEN_FIELDS + `.sort()` ดัน frozen หน้าสุดติดกัน. **บทเรียน: frozen-column Tabulator ต้องเรียงติดกันหน้าสุดเสมอ อย่าเชื่อ auto-collect**
7. **เลือก freeze เองได้ (รอบ 4, 0802cba):** โอขอ freeze/ปลด คอลัมน์ไหนก็ได้. ปุ่ม "ค้างซ้าย" ในเมนูคอลัมน์ + เมนูคลิกขวา; จำใน localStorage `yk_daily_frozen_v1` (default วันที่/คนขับ/ทะเบียน).
8. **GOTCHA (รอบ 5, a813b78): freeze คอลัมน์ใหม่ → freeze เดิมหลุด+ทับซ้อน!** (โอคลิกขวา freeze ลูกค้า → default หลุด). เหตุ: `applyFrozen` เดิมใช้ `updateColumnDefinition`+`moveColumn` ทีละคอลัมน์ → Tabulator ทำ frozen เดิมหลุด/มิสจัดตำแหน่ง. **แก้ที่ถูก: refactor `columns:[...]`→`buildColumns()` (อ่าน FROZEN_FIELDS ตั้ง frozen+sort ติดกันหน้าสุด); freeze toggle = `table.setColumns(buildColumns())` สร้างชุดใหม่ทั้งหมด atomic** (เชื่อถือได้กว่าแก้ทีละคอลัมน์มาก). setColumns รีเซ็ต hidden+header DOM → ต้อง `applyHidden()` + `attachHeaderContextMenu()` (กันผูกซ้ำด้วย dataset.ykCtx) ใหม่หลัง rebuild; cellEdited config→`table.on("cellEdited")`. **VERIFIED Chrome จริงผ่าน CDP (websockets stdlib + chrome --headless=new --remote-debugging-port, findTable getColumns getDefinition().frozen): freeze ลูกค้า→default ยังค้าง+contiguous, unfreeze หลัง rebuild ทำงาน, persist localStorage**. บทเรียน: dynamic freeze Tabulator อย่าแก้ทีละคอลัมน์ ใช้ setColumns ทั้งชุด; **มี CDP harness ขับ browser จริงได้แล้ว (เลิก "ยืนยันทางอ้อม")**

**Verify:** repro TestClient — no-auth→401 JSON, authed→persist (FIX_OK/5555); node --check JS OK; /daily render 200; pytest grid 2/2 + rbac 6/6 (incl new test_unauthenticated_api_returns_401_json) pass.
**ข้อจำกัด:** ยืนยันบั๊ก A ทางอ้อม (ไม่มี browser automation ในเครื่อง) — commitOpenEditor เป็น fix มาตรฐานของ commit-race + safe (แค่เพิ่มโอกาส commit ไม่ลบของเดิม). ถ้ายังไม่หาย step ถัดไป = instrument browser จริง.

เกี่ยว: [[reference-mvp-server-deploy]] (live = app.yklogistics.uk), [[feedback-merge-and-deploy-without-preview]]
