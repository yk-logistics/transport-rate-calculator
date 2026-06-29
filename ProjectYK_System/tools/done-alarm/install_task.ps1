# ติดตั้ง Scheduled Task เปิด alarm service ตอน logon (รันใต้ user เพื่อให้เข้าถึงเสียง)
$ErrorActionPreference = "Stop"
$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$py     = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
$script = Join-Path $here "alarm_service.py"
if (-not (Test-Path $py))     { throw "python not found: $py" }
if (-not (Test-Path $script)) { throw "service not found: $script" }

$action  = New-ScheduledTaskAction -Execute $py -Argument "`"$script`"" -WorkingDirectory $here
$trigger = New-ScheduledTaskTrigger -AtLogOn
$set     = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
             -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$set.ExecutionTimeLimit = "PT0S"  # ไม่จำกัดเวลา (service รันยาว)

Register-ScheduledTask -TaskName "Claude_Done_Alarm" -Action $action -Trigger $trigger `
  -Settings $set -RunLevel Limited -Force | Out-Null
Write-Host "registered Claude_Done_Alarm; starting now..."
Start-ScheduledTask -TaskName "Claude_Done_Alarm"
