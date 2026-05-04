#Requires -Version 5.1
<#
.SYNOPSIS
  ย้าย SQLite (app.db) → Neon Postgres ครั้งเดียว — ขั้นที่ทำบนเครื่องได้ก่อนเปิด Render

.DESCRIPTION
  1) pip install -r ProjectYK_System/app/requirements.txt
  2) ตั้ง $env:DATABASE_URL แล้วรัน sqlite_to_postgres.py --wipe
  3) พิมพ์รายการ env สำหรับวางใน Render

  Neon + Render ต้องสมัครและวางรหัสเอง — สคริปต์นี้ไม่รู้ connection string ของคุณ

.EXAMPLE
  # วาง connection string จาก Neon (มี sslmode ตามที่ Neon บอก)
  $env:DATABASE_URL = "postgresql://user:pass@ep-xxx.region.aws.neon.tech/neondb?sslmode=require"
  .\ProjectYK_System\tools\cloud_demo_setup.ps1

.EXAMPLE
  .\ProjectYK_System\tools\cloud_demo_setup.ps1 -DatabaseUrl "postgresql://..."
#>
param(
  [string] $DatabaseUrl = "",
  [string] $SqlitePath = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$AppDir = Join-Path $RepoRoot "ProjectYK_System\app"
$Req = Join-Path $AppDir "requirements.txt"
$Migrate = Join-Path $RepoRoot "ProjectYK_System\tools\sqlite_to_postgres.py"

if (-not (Test-Path $Req)) {
  Write-Error "Not found: $Req"
}

if (-not $DatabaseUrl) {
  if ($env:DATABASE_URL) {
    $DatabaseUrl = $env:DATABASE_URL
  } else {
    Write-Host ""
    Write-Host "=== Neon: คัดลอก Connection string จากแดชบอร์ด ===" -ForegroundColor Cyan
    Write-Host "วางทั้งบรรทัดแล้ว Enter (จะเก็บใน session นี้เท่านั้น ไม่บันทึกลงไฟล์)" -ForegroundColor Gray
    $DatabaseUrl = Read-Host "DATABASE_URL"
  }
}

if (-not $DatabaseUrl.Trim()) {
  Write-Error "ต้องมี DATABASE_URL (จาก Neon)"
}

$env:DATABASE_URL = $DatabaseUrl.Trim()

Write-Host "`n=== pip install ===" -ForegroundColor Cyan
python -m pip install --upgrade pip
python -m pip install -r $Req

$extra = @()
if ($SqlitePath) {
  $extra += "--sqlite", (Resolve-Path $SqlitePath).Path
}

Write-Host "`n=== ย้าย SQLite → Postgres (--wipe ล้างตารางบน Postgres เป้าหมาย) ===" -ForegroundColor Yellow
python $Migrate @extra --wipe

Write-Host "`n=== เสร็จแล้ว — ขั้นต่อไป (Render) ===" -ForegroundColor Green
Write-Host "1) Push โค้ด repo นี้ขึ้น GitHub ที่ Render จะดึง (ต้องมีโฟลเดอร์ ProjectYK_System/ และ render.yaml ที่ราก)"
Write-Host "2) Render → New Web Service → Blueprint หรือเลือก repo + ใช้ render.yaml"
Write-Host "3) Environment → ใส่ค่าดังนี้ (DATABASE_URL ใช้ตัวเดียวกับที่เพิ่งรัน):"
Write-Host ""
Write-Host "   DATABASE_URL = <วางจาก Neon เหมือนที่ใช้ย้ายข้อมูล>"
Write-Host "   YK_PREVIEW_AUTH = 1"
Write-Host "   YK_PREVIEW_USER = yk"
Write-Host "   YK_PREVIEW_PASSWORD = <รหัสยาว แชร์เฉพาะพ่อ/คนใน>"
Write-Host ""
Write-Host "4) Deploy แล้วเปิด URL — เบราว์เซอร์จะถาม HTTP Basic"
Write-Host "คู่มือเต็ม: ProjectYK_System\docs\HOSTING_FREE_DEMO_TH.md`n"
