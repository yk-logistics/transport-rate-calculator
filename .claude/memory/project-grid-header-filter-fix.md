---
name: project-grid-header-filter-fix
description: daily-grid Excel header filter ไม่ apply เมื่อเปลี่ยนชุดเลือกโดยไม่ล้างก่อน — fix = table.refreshFilter() หลัง success()
metadata: 
  node_type: memory
  type: project
  originSessionId: a7be03e9-a1b6-49f9-babb-fcf28b790466
---

DONE+deployed 30มิ.ย. (main b8a4d2f): โอเจอบั๊ก daily-grid — ติ๊ก Excel-style header filter (makeExcelFilter), เอาติ๊กออกแล้วติ๊กอันอื่น → ไม่เปลี่ยน; ต้องติ๊กทั้งหมด→เอาออกทั้งหมด→เลือกใหม่ ถึง apply.

**Root cause (พิสูจน์ด้วย headless repro):** Tabulator 6.2.1 custom header-filter editor เรียก `success(value)` set ค่า filter แต่ตารางไม่ re-run กรองเมื่อเรียก success() ด้วยค่าใหม่ติดๆ กัน (ชุด A→ชุด B) — re-run เฉพาะตอนผ่าน null/clear (ALL). เลยอธิบาย "ทำผ่าน all/clear แล้วเวิร์ค".

**Fix (1 บรรทัด):** เรียก `table.refreshFilter()` หลัง `success()` ใน `applyFilter()` (templates/daily_grid.html ~บรรทัด 514). บังคับประเมินตัวกรองใหม่ทุกครั้ง.

**วิธีพิสูจน์ (debug tester ใหม่):** `tools/grid_filter_check/grid_filter_repro.html` — Tabulator 6.2.1 vendored + copy ของ makeExcelFilter/excelFilterFunc + 5 sequence (A→B, clear, ALL−C, {A,B}→{A,C}, C→A). รันด้วย Chrome headless `--screenshot` → อ่านป้าย FIX=true ALL_PASS / FIX=false SOME_FAIL. **GOTCHA Chrome บน Windows:** ต้องใช้ URL เต็ม `file:///C:/...` (path `/c/...` ของ MSYS → ERR_FILE_NOT_FOUND, ทำให้ --dump-dom ออกว่าง); ตัดสินผลด้วย screenshot (ไม่ใช่ --dump-dom ที่ออกว่างบ่อยกับ virtual-time). ไม่มี UI test harness ใน repo (CLAUDE.md ระบุ no test suite) — นี่เป็น tester ตัวแรกสำหรับ grid.

related: [[reference-chrome-headless-pdf]], [[project-daily-grid-save-auth-redirect]], [[project-lcb-bigc-jun-payroll-review]]
