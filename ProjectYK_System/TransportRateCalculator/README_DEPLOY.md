# One-Click Deploy (GitHub Pages)

ไฟล์: `deploy.ps1`

สคริปต์นี้จะคัดลอก `transport_rate_calculator.html` ไปเป็น `index.html` ใน repo แล้ว commit/push ให้อัตโนมัติ

## ใช้งานเร็วที่สุด

เปิด PowerShell ที่โฟลเดอร์ `ProjectYK_System/TransportRateCalculator` แล้วรัน:

```powershell
.\deploy.ps1 -RepoPath ".."
```

> `-RepoPath ".."` หมายถึงให้เอา `index.html` ไปวางที่โฟลเดอร์แม่ (รูปแบบที่ใช้กับ GitHub Pages ส่วนใหญ่)

## One-click icon (ดับเบิลคลิก)

ใช้ไฟล์ `deploy_one_click.bat` ได้เลย:

- ดับเบิลคลิก `deploy_one_click.bat`
- สคริปต์จะเรียก `deploy.ps1` ให้อัตโนมัติ
- ถ้า repo ไม่ได้อยู่โฟลเดอร์แม่ ให้แก้บรรทัด `REPO_PATH` ในไฟล์ `.bat`

## ตัวอย่างที่ใช้บ่อย

- คัดลอก + commit + push (ปกติ)

```powershell
.\deploy.ps1 -RepoPath ".." -CommitMessage "Update calculator UI and sync"
```

- คัดลอก + commit แต่ยังไม่ push

```powershell
.\deploy.ps1 -RepoPath ".." -NoPush
```

- ถ้า repo อยู่คนละ path

```powershell
.\deploy.ps1 -RepoPath "C:\path\to\your-repo"
```

## หมายเหตุ

- ถ้า path ที่ระบุไม่ใช่ git repo สคริปต์จะคัดลอกไฟล์อย่างเดียว (ไม่ commit/push)
- ถ้าไม่มีการเปลี่ยนแปลงของ `index.html` สคริปต์จะไม่ commit ใหม่
- ถ้าขึ้น `Please tell me who you are` ให้ตั้งชื่อผู้ใช้ git ครั้งแรก:

```powershell
git config --global user.name "<ชื่อที่แสดงใน commit>"
git config --global user.email "<อีเมลที่ผูกกับ GitHub>"
```
