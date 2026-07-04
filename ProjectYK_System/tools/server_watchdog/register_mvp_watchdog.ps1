# Register YK_MVP_HEALTHPOLL - run watchdog every 5 minutes as SYSTEM (ASCII only for PS5.1)
$ErrorActionPreference = "Stop"
$py = "C:\Users\yklog\AppData\Local\Python\pythoncore-3.12-64\python.exe"
if (-not (Test-Path $py)) { $py = "C:\Users\yklog\YK_MVP\app\.venv\Scripts\python.exe" }
$script = "C:\Users\yklog\YK_MVP\mvp_health_poll.py"
if (-not (Test-Path $script)) { Write-Output "FAIL: missing $script"; exit 1 }

schtasks /Create /F /TN "YK_MVP_HEALTHPOLL" /SC MINUTE /MO 5 /RU SYSTEM `
  /TR "`"$py`" `"$script`"" | Out-Null
Write-Output "task registered"

# run once now and show output
& $py $script
if ($LASTEXITCODE -ne 0) { Write-Output "FAIL: first run exit $LASTEXITCODE"; exit 1 }
schtasks /Query /TN "YK_MVP_HEALTHPOLL" /FO LIST | Select-String "TaskName","Status","Next Run"
Write-Output "RESULT OK"
