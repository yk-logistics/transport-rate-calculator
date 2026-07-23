---
name: reference-msi-laptop-fan-ec
description: "เครื่องโน้ตบุ๊กโอ (MSI GF63, MS-16R8) โดน spoof ชื่อเครื่อง — คุมพัดลมผ่าน EC ตรงด้วย ec-probe; ปุ่ม FanBoost.bat บน Desktop"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f2a687e8-4419-4e2d-9df2-35f04db342ed
---

เครื่องที่รัน Claude Code (โน้ตบุ๊กโอ) = **MSI GF63 Thin (บอร์ด MS-16R8)** แต่ SMBIOS ช่อง Manufacturer/Model โดน HWID spoofer เขียนทับเป็น `1GOD-Arena54543-34657678` (10 ก.ค. 2026) → MSI Center/โปรแกรมพัดลมของ vendor หาเครื่องไม่เจอถาวร จนกว่าจะแก้ SMBIOS กลับ (งาน flash แยก เสี่ยง ยังไม่ทำ)

ทางแก้ที่ใช้อยู่: คุมพัดลมผ่าน EC ตรง (ผัง msi-ec ยืนยันกับเครื่องจริง — ทดสอบเขียนตารางแล้วพัดลมวิ่งตาม):
- `0x98` bit 7 = Cooler Boost (0x86 เปิด / 0x06 ปิด) — **รีเซ็ตเองเมื่อรีบูต**
- `0xD4` = fan mode (0x0D = auto); ตารางโค้งใช้ได้เลยในโหมด auto ไม่ต้องสลับ advanced
- โค้งพัดลม: temp thresholds CPU `0x6A-0x70` (50,60,65,70,75,80,100) / speeds CPU `0x72-0x78`, GPU `0x8A-0x90` (โรงงาน 0,40,50,60,70,80,85; ตั้งใหม่เป็น 0,45,55,65,80,90,100) — **ตารางก็รีเซ็ตตอนรีบูต ต้องตั้งกลับ**
- realtime: CPU temp `0x68`, CPU fan% `0x71`, GPU temp `0x80` (0=dGPU หลับ), GPU fan% `0x89`
- เครื่องมือ: NoteBook FanControl 1.6.3 ลงไว้แล้ว (ใช้แค่ `ec-probe.exe`; config NBFC ไม่มีรุ่น MSI)

ชุดโปรแกรมที่สร้าง (10 ก.ค. 2026) ใน `C:\Users\guole\FanTuner\`:
- `FanTuner.ps1` — GUI สไลเดอร์ 7 ช่วงอุณหภูมิ + preset โรงงาน/แรง/เงียบ + boost; เซฟลง `curve.json`; ปุ่มลัด Desktop `FanTuner.bat`
- `FanTray.ps1` — ไอคอน tray 3 ตัว CPU/GPU/SSD (11 ก.ค.: แยกจากเดิมตัวเดียว) เลขสีตามความร้อน (ขาว/ส้ม/แดง — CPU·GPU 70/85, SSD 60/70) + ขีดสีใต้เลขบอกตัว (ฟ้า=CPU เขียว=GPU ม่วง=SSD); GPU หลับ/SSD อ่านไม่ได้โชว์ `-`; balloon เตือน CPU ≥90°C + เมนูคลิกขวาใช้ร่วมทั้ง 3 ไอคอน; ตอนสตาร์ทเรียก `ApplyCurve.ps1` ตั้งโค้งกลับ; 13 ก.ค.: tooltip โชว์ค่า Max ตั้งแต่เปิดโปรแกรม (temp ทั้ง 3 ตัว + พัดลม% — กรองค่าหลอน temp 1-105 / fan 1-100) + เมนู "รีเซ็ตค่าสูงสุด"; tooltip NotifyIcon จำกัด 63 ตัวอักษร (PS 5.1/.NET Framework)
- Scheduled task `MSI_FAN_TRAY` (logon, RunLevel Highest, **ExecutionTimeLimit PT0S กัน 72h kill**) — verified รันจริง
- `C:\Users\guole\Desktop\FanBoost.bat` — toggle boost เดี่ยวๆ (ของเดิม ยังใช้ได้)

Gotcha:
- อย่าเชื่อ Win32_ComputerSystem บนเครื่องนี้ — ดูรุ่นจริงจาก Win32_BaseBoard แทน
- ec-probe อ่านพลาดคืนค่า 0/ค่าเก่าเป็นครั้งคราว — ต้องอ่านซ้ำเอาค่าที่ตรงกัน 2 ครั้ง (ทุกสคริปต์ทำแล้ว)
- ps1 พวกนี้มีภาษาไทย → ต้องเป็น UTF-8 **มี BOM** (Windows PowerShell 5.1 อ่าน no-BOM เพี้ยน)
