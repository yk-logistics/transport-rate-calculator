---
name: project-daily-lcb-sheet
description: "The \"Daily LCB\" (เดลี่แหลม) Google Sheet — structure, the driver-name validation fix, formula layout"
metadata: 
  node_type: memory
  type: project
  originSessionId: 6182d152-ce07-4450-aa05-40ab887fdf30
---

"Daily LCB" / เดลี่แหลม / เดลี่แหลมฉบัง = โอ's LCB daily-job Google Sheet (transport prices + driver pay).
Sheet id: `1Tm1i7kHGkiYtNwM-HQWEnQReg6VZmLzj7T1DjXr8zqg` (the converted real-Sheet; the old `1Ta1axqauh...` is the .xlsx original — don't use).
Access via [[reference-google-sheets-access]].

**Layout:** ~43 monthly tabs named `Daily 16.MM.YY - 15.MM.YY` (LCB cycle 16→15, matches YK pay cycle). Plus a `ฐานข้อมูล` master tab: col A=driver names (A2:A200), B=phone, C=start date, E=customers, G=Type, I=subcontractors, J=plates.
Column layout DRIFTS across years — driver-name col is **F** in old (65–67) tabs, **E** in newer (67+) tabs. Always find columns by header text in row 2, never by fixed letter.

**Driver-name validation fix (2026-06-17):** col E/F has a strict ONE_OF_RANGE dropdown sourced from `ฐานข้อมูล`. Latest tab's rule was `$A$23:$A$200` which SKIPPED the active drivers living in A2:A22 → 460 false red flags ("Input must fall within specified range"). Fixed the latest tab (`Daily 16.01.69 - 15.02.69`) by widening to `$A$2:$A$200` → 0 flags. **Old tabs intentionally left as-is** (โอ: past data already paid, don't touch — their flags are real ex-drivers not in the list).

**Formulas (latest tab) are clean/uniform:** X (รวมค่าใช้จ่าย)=`SUM(P:V)-W`; Z (รวมเก็บค่าขนส่ง)=`SUM(X:Y)`; row1 totals use `SUBTOTAL(9,...)`. Rows with X/Z formula deliberately blank = special "เก็บ %" rows (โอ confirmed, not a bug). Open: row1 lacks SUBTOTAL for U (ค่าชั่งน้ำหนัก) & X — โอ said discuss later, don't add yet.

Backups of edited tab in `reports/daily_lcb_backup_*.json`.
