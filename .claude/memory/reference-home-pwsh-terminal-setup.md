---
name: reference-home-pwsh-terminal-setup
description: "HOME machine (.178) terminal setup — Desktop \"Claude (Admin)\" shortcut, pwsh 7.6.3, Windows Terminal fixes Thai tone-mark dropping"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 4e010a1e-f0f6-41d5-bf71-63414e3a811d
---

เครื่อง HOME (HOME\guole, .178) terminal setup สำหรับเปิด Claude Code:

- **Desktop shortcut "Claude (Admin)"** = ทางเข้าหลัก → เปิด **Windows Terminal (Admin)** → pwsh 7.6.3 → cd Project YK → `claude`. Run-as-Admin flag ติดแล้ว.
- **PowerShell 7.6.3** ติดตั้งแบบ MSI ที่ `C:\Program Files\PowerShell\7\pwsh.exe`. winget ตามเวอร์ชันช้า (ค้างที่ 7.6.2) → ถ้าจะอัปต้องโหลด MSI ตรงจาก GitHub release `PowerShell/PowerShell/releases/tags/vX.Y.Z` (asset `*win-x64.msi`).
- **Store/Appx PowerShell ถอนแล้ว** — เคยมี Microsoft.PowerShell appx (Store) วางใน PATH ก่อน Program Files ทำให้ `pwsh` หยิบตัวเก่าเสมอ. ⚠️ ห้าม `Remove-AppxPackage` ตัว pwsh ที่ session ปัจจุบันรันอยู่ — มันจะ kill session กลางคัน (เคยเกิดแล้ว). ถอนจากหน้าต่างอื่นที่ไม่ได้รันบนตัวนั้น.

**วรรณยุกต์ไทยหาย/ตัวอักษรเพี้ยน**: ต้นเหตุคือ **conhost เก่า** เรนเดอร์ combining marks ไทยไม่ได้ — encoding (UTF-8/cp65001) ไม่ใช่ปัญหา, แก้ฟอนต์อย่างเดียวก็ไม่พอ. ทางแก้จริง = ใช้ **Windows Terminal** (Cascadia Code + font fallback เรนเดอร์ไทยถูก). Sarabun ลงไว้แล้ว (per-user) เผื่องานอื่น แต่ไม่ใช่ตัวแก้หลัก.

เกี่ยวข้อง: [[reference-mvp-server-deploy]] (เครื่อง .197 คนละตัว, อย่าสับสน).
