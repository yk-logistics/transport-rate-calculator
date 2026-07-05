# _deploy_remote.ps1 - runs ON THE SERVER (sent via scp, executed by deploy_mvp.sh).
#
# Why a file instead of inline SSH: the server shell is PowerShell and nested quoting
# over SSH gets mangled (memory: reference-deploy-via-tailscale). Sending a .ps1 and
# running it by path is the only reliable way.
#
# It does the cutover + SELF-VERIFY so the deploy proves itself instead of the human
# eyeballing it. Every check prints a PASS/FAIL line; any FAIL sets $fail and the script
# exits 1 at the end so the caller (bash) sees a non-zero exit.
#
# Params:
#   -ExpectMarkers  comma-separated ASCII strings that MUST exist in main.py / templates
#                   on the server after copy (guards against revert / stale code).
#                   Use ASCII only - Thai Select-String over SSH gives false negatives
#                   (memory: reference-mvp-deploy-restart-gotcha).
#   -DbDeployed     "1" if app.db was just copied (then we verify byte-size match too).
#   -DbLocalSize    expected app.db size in bytes (from the Dev side) when -DbDeployed 1.

param(
    [string]$ExpectMarkers = "",
    [string]$DbDeployed   = "0",
    [string]$DbLocalSize  = "0"
)

$ErrorActionPreference = "Stop"
$AppDir   = "C:/Users/yklog/YK_MVP/app"
$MainPy   = "$AppDir/main.py"
$DbFile   = "$AppDir/app.db"
$fail     = $false
function Pass($m){ Write-Output "PASS  $m" }
function Fail($m){ Write-Output "FAIL  $m"; $script:fail = $true }

# --- 0. record deploy time so we can prove the NEW process started after it -----------
$deployStamp = (Get-Item $MainPy).LastWriteTime
Write-Output "INFO  main.py on disk mtime = $deployStamp"

# --- 1. (optional) DB byte-size guard - never restart onto a truncated/partial DB ------
if ($DbDeployed -eq "1") {
    if (-not (Test-Path $DbFile)) { Fail "app.db missing after copy" }
    else {
        $sz = (Get-Item $DbFile).Length
        if ("$sz" -eq "$DbLocalSize") { Pass "app.db byte-size matches Dev ($sz)" }
        else { Fail "app.db size mismatch: server=$sz expected=$DbLocalSize (partial scp?) - NOT restarting" }
    }
    if ($fail) { Write-Output "RESULT FAIL"; exit 1 }   # bail before touching the live app
}

# --- 2. safe cutover: stop task, free port 8010 by PID + YK_MVP cmdline (NOT bare .venv)
#        bare \.venv also matches the LINE archiver on 8020 (memory gotcha).
Stop-ScheduledTask -TaskName "YK_MVP_APP" -ErrorAction SilentlyContinue
$port8010 = Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue
if ($port8010) {
    foreach ($pid8010 in ($port8010.OwningProcess | Select-Object -Unique)) {
        Stop-Process -Id $pid8010 -Force -ErrorAction SilentlyContinue
    }
}
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'YK_MVP' -and $_.CommandLine -match 'main\.py' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# wait until 8010 is actually free (max ~10s)
$freed = $false
for ($i=0; $i -lt 20; $i++) {
    if (-not (Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue)) { $freed = $true; break }
    Start-Sleep -Milliseconds 500
}
if ($freed) { Pass "port 8010 freed before restart" } else { Fail "port 8010 still held - old code may persist" }

# --- 3. relaunch + wait for it to bind ------------------------------------------------
Start-ScheduledTask -TaskName "YK_MVP_APP"
$up = $false
for ($i=0; $i -lt 30; $i++) {
    if (Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue) { $up = $true; break }
    Start-Sleep -Milliseconds 600
}
if ($up) { Pass "app re-bound port 8010" } else { Fail "app did not bind 8010 within ~18s" }

# --- 4. prove it's the NEW process (started AFTER this deploy), not the stale one ------
$newOwner = Get-NetTCPConnection -LocalPort 8010 -State Listen -ErrorAction SilentlyContinue
if ($newOwner) {
    $opid  = ($newOwner.OwningProcess | Select-Object -First 1)
    $proc  = Get-Process -Id $opid -ErrorAction SilentlyContinue
    if ($proc -and $proc.StartTime -ge $deployStamp.AddSeconds(-5)) {
        Pass "8010 owned by fresh pid $opid (started $($proc.StartTime))"
    } else {
        Fail "8010 owner pid $opid started $($proc.StartTime) - BEFORE deploy ($deployStamp): stale code still serving"
    }
}

# --- 5. archiver (port 8020) must still be up - we must not have killed it -------------
if (Get-NetTCPConnection -LocalPort 8020 -State Listen -ErrorAction SilentlyContinue) {
    Pass "LINE archiver (8020) still up"
} else {
    Fail "port 8020 down - cutover may have killed the LINE archiver"
}

# --- 6. code-content guard: required ASCII markers present on server files -------------
if ($ExpectMarkers.Trim().Length -gt 0) {
    # สแกน main.py + templates + services/*.py (เดิมไม่สแกน services → marker ของ
    # change ใน payroll.py/payroll_slip.py ฯลฯ FAIL หลอกซ้ำสอง — memory ayu-mao-pertrip)
    $files = @($MainPy) `
        + (Get-ChildItem "$AppDir/templates" -Filter *.html -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName }) `
        + (Get-ChildItem "$AppDir/services" -Filter *.py -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
    foreach ($mk in ($ExpectMarkers -split ',')) {
        $m = $mk.Trim(); if ($m.Length -eq 0) { continue }
        $hit = Select-String -SimpleMatch -Pattern $m -Path $files -List -ErrorAction SilentlyContinue
        if ($hit) { Pass "marker present: $m" } else { Fail "marker MISSING (revert/stale?): $m" }
    }
}

if ($fail) { Write-Output "RESULT FAIL"; exit 1 } else { Write-Output "RESULT OK"; exit 0 }
