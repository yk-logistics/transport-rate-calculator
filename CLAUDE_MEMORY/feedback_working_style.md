---
name: feedback-working-style
description: กฎการทำงานร่วมกัน — สิ่งที่ต้องทำและห้ามทำ เมื่อทำงานกับโอ
metadata:
  type: feedback
---

## ตอบสั้น — ไม่สรุปท้าย

อย่าสรุปว่า "ทำอะไรไปแล้ว" ท้าย response ทุกครั้ง — โออ่าน diff ได้เอง

**Why:** โอต้องการความเร็ว ไม่ต้องการคำอธิบายซ้ำ
**How to apply:** จบที่ผลลัพธ์จริง ไม่มี bullet "สรุปสิ่งที่ทำ"

---

## ห้ามเดาเรื่องเงิน

ถ้าคำสั่งกำกวมเรื่อง: ไซต์, รอบเดือน (วิ่ง vs จ่าย), ชื่อคนขับคล้ายกัน, cross-site — **ถามก่อนเสมอ**

**Why:** ผิดเงียบๆ ในระบบ payroll/petty cash กู้คืนยาก
**How to apply:** เตือนทันทีเมื่อเจอ ambiguity ที่กระทบตัวเลขเงิน

---

## ลำดับงาน payroll: BigC → LCB → AYU

ถ้าไม่มีคำสั่งเจาะจง ให้ทำตามลำดับนี้

**Why:** โอยืนยันในแชต session #8
**How to apply:** เมื่อต้องเลือก site ที่จะทำก่อน ใช้ลำดับนี้

---

## ใช้ภาษาไทยเสมอ

ตอบเป็นภาษาไทยในทุกการสื่อสาร ยกเว้น code, key, path, command

**Why:** โอสื่อสารเป็นไทย ไม่ต้องการอ่านอังกฤษยาว
**How to apply:** ทุก response ยกเว้น inline code

---

## งานเล็ก → เริ่ม Ultra-Lean

งานที่ scope ชัด/เล็ก ให้เริ่มจาก `tools/CC_ULTRA_LEAN_5LINES.txt` ก่อน
fallback ไป `CC_LEAN_START.txt` ถ้าต้องการ context เพิ่ม

**Why:** ประหยัด token, เซสชันเร็ว
**How to apply:** ไม่อ่าน CHANGELOG/CONTEXT_LOG ถ้าไม่จำเป็น

---

## งานกระทบเงิน → รอบคอบเต็มรูปแบบ

งานที่แตะ: import, payroll engine, petty cash, billing — ต้องอ่านครบตาม bootstrap
ต้องระบุวิธี preflight / จำนวนแถวที่กระทบ ก่อนทำ

**Why:** ข้อมูลเงินผิดกู้ยากมาก
**How to apply:** ไม่ข้ามขั้นตอน preflight แม้โอจะรีบ

---

## ทำให้จบเอง อย่าให้โอลองผิดลองถูก

โออยากให้ Claude แก้ปัญหาให้เสร็จ ไม่ใช่แค่บอกขั้นตอน

**Why:** โอเบื่อการ debug ไป-กลับหลายรอบ ไม่ใช่ coder
**How to apply:** ถ้าแก้ได้เองผ่าน Bash/PowerShell ให้รันและยืนยันผลก่อนรายงาน อย่าสั่งให้โอรันเอง

---

## วิธีแก้ `claude` command ไม่อยู่ใน PATH บน Windows (จำไว้)

**อาการ:** `'claude' is not recognized` หรือ `The system cannot find the path specified` ใน cmd.exe

**สาเหตุ:** Explorer.exe ล็อค PATH ไว้ตั้งแต่ login — การติดตั้ง Node.js/npm หลัง login ไม่ถูกสืบทอดไปยัง cmd ใหม่

**วิธีแก้ถาวร (ทำครั้งเดียว ใช้ได้ตลอด):**

```powershell
# 1. สร้าง cmd AutoRun registry — inject PATH ทุกครั้งที่ cmd เปิด
$regPath = "HKCU:\Software\Microsoft\Command Processor"
if (!(Test-Path $regPath)) { New-Item -Path $regPath -Force | Out-Null }
$autorun = 'IF NOT DEFINED _NPMPATH (SET "_NPMPATH=1" & SET "PATH=%PATH%;C:\Program Files\nodejs;C:\Users\guole\AppData\Roaming\npm")'
Set-ItemProperty -Path $regPath -Name "AutoRun" -Value $autorun -Force

# 2. PowerShell profile (ถ้ายังไม่มี)
$psLine = '$env:PATH = "$env:PATH;C:\Program Files\nodejs;C:\Users\guole\AppData\Roaming\npm"'
if (!(Test-Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force | Out-Null }
if ((Get-Content $PROFILE -Raw) -notlike "*nodejs*") { Add-Content $PROFILE "`n$psLine" }
```

**ทดสอบ:** เปิด cmd ใหม่แล้วรัน `claude --version` ต้องได้ `2.1.153 (Claude Code)`
