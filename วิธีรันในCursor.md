# วิธีรันโปรแกรมเงินเดือน (payroll_system.py) ใน Cursor

โปรแกรมนี้เป็น **Python** ต้องรันผ่าน **Terminal (เทอร์มินัล)** หรือปุ่ม Run ใน Cursor

---

## วิธีที่ 1: เปิด Terminal ใน Cursor แล้วรันคำสั่ง (แนะนำ)

1. **เปิด Terminal**
   - กด **Ctrl + `** (ปุ่ม backtick อยู่ข้างปุ่ม 1)
   - หรือเมนูด้านบน: **Terminal** → **New Terminal**

2. **ตรวจสอบว่าอยู่โฟลเดอร์โปรเจกต์**
   - ใน Terminal จะเห็น path ประมาณ `c:\Users\Home\Desktop\Project YK`
   - ถ้าไม่อยู่ ให้พิมพ์:
     ```bash
     cd "c:\Users\Home\Desktop\Project YK"
     ```
     แล้วกด Enter

3. **รันโปรแกรม**
   - พิมพ์:
     ```bash
     python payroll_system.py
     ```
   - กด Enter

4. **ถ้าขึ้นว่า "python ไม่รู้จัก"**
   - ลองใช้:
     ```bash
     py payroll_system.py
     ```
   - บน Windows บางเครื่องใช้คำสั่ง `py` แทน `python`

5. **โปรแกรมจะถามทีละขั้น**
   - วันตัดรอบ (วว/ดด/ปปปป)
   - เลือกไฟล์ Master, Daily, สดย่อย, น้ำมัน (กดเลขแล้ว Enter)
   - เลือกชีท (กดเลขแล้ว Enter)
   - ตรวจสอบคอลัมน์ (Enter = ใช่, n = แก้)
   - ตอนจบ: ถามว่าอัปเดตยอดประกันกลับ Master หรือไม่

---

## วิธีที่ 2: รันด้วยปุ่ม Run (เล่นไฟล์เดียว)

1. **เปิดไฟล์** `payroll_system.py` (คลิกที่ไฟล์ใน Explorer ด้านซ้าย)

2. **กด Run**
   - กดปุ่ม **▶ Run** มุมขวาบนของ Cursor (หรือเหนือบรรทัดแรกของไฟล์)
   - หรือกด **Ctrl + F5** (รันโดยไม่เข้าโหมดดีบัก)

3. **ถ้ามีปุ่ม Run**
   - โปรแกรมจะรันใน Terminal ด้านล่างอัตโนมัติ
   - ถ้าไม่มีปุ่ม Run ใช้วิธีที่ 1 แทน

---

## วิธีที่ 3: รันจาก Command Prompt / PowerShell นอก Cursor

1. เปิด **Command Prompt** หรือ **PowerShell** (กด Win แล้วพิมพ์ `cmd` หรือ `powershell`)

2. ไปที่โฟลเดอร์โปรเจกต์:
   ```bash
   cd "c:\Users\Home\Desktop\Project YK"
   ```

3. รัน:
   ```bash
   python payroll_system.py
   ```
   หรือ
   ```bash
   py payroll_system.py
   ```

---

## ติดตั้ง Python / library ที่ขาด (ถ้ารันแล้ว error)

ถ้าขึ้นว่า **"python is not recognized"** = ยังไม่ได้ติดตั้ง Python หรือไม่ได้ใส่ใน PATH

- ดาวน์โหลด Python: https://www.python.org/downloads/
- ติดตั้ง时 เลือก **"Add Python to PATH"**
- ปิดแล้วเปิด Cursor ใหม่ แล้วลองรันอีกครั้ง

ถ้าขึ้นว่า **"No module named 'pandas'"** หรือ **"No module named 'openpyxl'"**:

- ใน Terminal (โฟลเดอร์ Project YK) พิมพ์:
  ```bash
  pip install -r requirements.txt
  ```
  หรือ
  ```bash
  pip install pandas openpyxl
  ```

---

## สรุปสั้นๆ

| ขั้นตอน | ทำอะไร |
|---------|--------|
| 1 | กด **Ctrl + `** เพื่อเปิด Terminal |
| 2 | พิมพ์ `cd "c:\Users\Home\Desktop\Project YK"` (ถ้าอยู่ที่อื่น) |
| 3 | พิมพ์ `python payroll_system.py` แล้วกด Enter |
| 4 | ตอบคำถามในโปรแกรม (วันตัดรอบ, เลือกไฟล์, เลือกชีท ฯลฯ) |

ผลลัพธ์จะได้ไฟล์ Excel ชื่อประมาณ **Payroll_V18_YYYYMMDD.xlsx** ในโฟลเดอร์ Project YK
