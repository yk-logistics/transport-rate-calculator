---
name: reference-google-drive-access
description: Claude อ่าน Google Drive (Excel/ไฟล์) ของโอผ่าน service account + Drive API — วิธี list/download ไฟล์จาก Drive
metadata: 
  node_type: memory
  type: reference
  originSessionId: 9c311e54-7995-433c-9140-7be9415aba8a
---

Claude เข้าถึง **Google Drive** ของโอได้แล้ว (ต่อยอดจาก [[reference-google-sheets-access]] ที่อ่านได้แค่ Google Sheets ผ่าน gspread).

**Setup (ทำเสร็จ 1 ก.ค. 2026):**
- ใช้ service account เดิม `yk-sheets-editor@noble-history-446303-e4.iam.gserviceaccount.com` (key = `noble-history-446303-e4-c36409a0122c.json` ที่ราก repo, gitignored)
- เปิด **Google Drive API** ใน GCP project `noble-history-446303-e4` แล้ว (โอกด Enable เอง)
- ลง `google-api-python-client` ใน **venv ของแอป** `ProjectYK_System/app/.venv/Scripts/python.exe` (global python ไม่มี gspread/googleapiclient — ต้องใช้ venv นี้เสมอ)
- โอแชร์โฟลเดอร์ให้ service account (Viewer) แล้ว list/download ได้

**วิธีใช้:** helper script `drive_pull.py` (เก็บใน scratchpad; ย้ายเข้า tools/ ได้ถ้าจะใช้ถาวร):
- `list <folder_id>` (recursive), `get <file_id> [out]`, `all <folder_id> <outdir>`
- Google-native Sheet → export เป็น .xlsx อัตโนมัติ; .xlsx ใน Drive → download ตรง

**GOTCHA สำคัญ:**
1. **ห้าม recurse ทั้งต้นไม้ทีเดียว** — จะ timeout (โฟลเดอร์ "ใบวางบิล LCB" มี 44 ลูกค้า × หลายเดือน × หลายไฟล์). ให้ **list ทีละชั้น** (ลูกค้า→เดือน→ไฟล์): 1 ชั้น = ~1 วินาที เร็วมาก. ต้อง lazy load.
2. **Console encoding** — print ภาษาไทยผ่าน bash/PowerShell crash (cp1252). เขียนผลลง UTF-8 file แล้ว Read กลับ (`sys.stdout.buffer.write(...encode("utf-8"))`).
3. **Network call ใน sandbox บางทีค้าง** → รัน `run_in_background` แล้ว poll output file.
4. list ไฟล์ต้องส่ง `supportsAllDrives=True, includeItemsFromAllDrives=True`.

**โฟลเดอร์ "ใบวางบิล LCB"** (ID `1kuME7KipmIp_P4NFvbcXlZCXzH2uH6n4`, ใต้ ไดรฟ์ของฉัน>บิลฝั่งแหลมฉบัง) = ใบวางบิลลูกค้ารายเที่ยว 44 ราย, แต่ละรายมีโฟลเดอร์เดือน `M.YYYY` (เช่น 6.2026) + ปี (2024/2025) ข้างใน. โครงไฟล์ = 2 ชีท `ปะหน้าขนส่ง` + `ค่าขนส่ง`.

related: [[reference-google-sheets-access]] [[project-cy-kb-payout-calculator]]
