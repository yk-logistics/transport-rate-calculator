# S1 ชั้น 3 — เครื่อง Dev (โอ) ดูดชุด backup ของร้อนคืนล่าสุดจาก server ผ่าน Tailscale
# ลงทะเบียนเป็น scheduled task YK_PULL_BACKUP (ทุกวัน 09:30 + ตอน logon) — เครื่องปิดอยู่ = ข้าม รอบหน้าดูดตามทัน
# สำเนานี้ = สำเนา "นอกเครื่อง server" ตัวหลัก ระหว่างชั้น Drive ยังรอ OAuth ของโอ
param(
  [string]$Server = "yklog@100.97.150.114",
  [string]$RemoteDaily = "D:/YK_BACKUPS/daily",
  [string]$LocalDir = "C:\Users\guole\YK_BACKUPS_MIRROR",
  [int]$Keep = 14
)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force $LocalDir | Out-Null
$log = Join-Path $LocalDir "pull.log"
function L($m) { ("[{0:yyyy-MM-dd HH:mm:ss}] {1}" -f (Get-Date), $m) | Tee-Object -FilePath $log -Append }
try {
  # หาไฟล์คืนล่าสุดบน server (ชื่อมี timestamp → เรียงชื่อ = เรียงเวลา)
  $latest = (ssh $Server "powershell -NoProfile -Command Get-ChildItem $RemoteDaily -Filter yk_hot_*.zip -Name | Sort-Object | Select-Object -Last 1") | Select-Object -Last 1
  $latest = ($latest | Out-String).Trim()
  if (-not $latest) { L "FAIL: no backup file on server"; exit 1 }
  $dest = Join-Path $LocalDir $latest
  if (Test-Path $dest) { L "skip: already have $latest"; exit 0 }
  scp -q "${Server}:$RemoteDaily/$latest" $dest
  $mb = [math]::Round((Get-Item $dest).Length / 1MB, 1)
  if ($mb -lt 1) { L "FAIL: $latest looks truncated ($mb MB)"; Remove-Item $dest -Force; exit 1 }
  L "OK pulled $latest ($mb MB)"
  # หมุนเวียนเก็บ $Keep ชุดล่าสุด
  Get-ChildItem $LocalDir -Filter "yk_hot_*.zip" | Sort-Object Name -Descending |
    Select-Object -Skip $Keep | ForEach-Object { L ("rotate: delete " + $_.Name); Remove-Item $_.FullName -Force }
  exit 0
} catch {
  L ("FAIL: " + $_.Exception.Message)
  exit 1
}
