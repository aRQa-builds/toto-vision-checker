<#
Keeps the web checker (P4-02) running on Grayskull: registers it as a Windows
scheduled task so it starts by itself. The task runs tools\web-service.cmd,
which starts the server again 10 s after it stops for any reason. (Task
Scheduler's own restart setting only covers a task that fails to launch, not a
server that dies later, so the loop does that job.)

Default: starts when you log on to Windows (no admin needed).
-AtStartup: starts when the PC boots, even before anyone logs on. Needs an
            Administrator PowerShell; runs as you without storing a password
            (S4U), which is fine because the server only listens on 127.0.0.1.

The server runs hidden and writes to logs\web.log (each start and stop is logged).
Running this script again is safe: it stops the old copy first, then starts fresh. It listens on
http://127.0.0.1:8765 only; the Cloudflare tunnel (P4-03) is what makes it public.
After starting it checks /api/health and every install file (manifest, service
worker, offline page, icons), so a server running older code is caught.

After changing any .py file, run this script again (or end the python process;
the loop restarts it): Python loads routes once, at start.

Usage (PowerShell, in the project folder):
  powershell -ExecutionPolicy Bypass -File tools\setup-web.ps1              # register (at logon) and start now
  powershell -ExecutionPolicy Bypass -File tools\setup-web.ps1 -AtStartup   # register (at boot), admin window
  powershell -ExecutionPolicy Bypass -File tools\setup-web.ps1 -Stop        # stop it now (stays registered)
  powershell -ExecutionPolicy Bypass -File tools\setup-web.ps1 -Disable     # stop and don't start again
  powershell -ExecutionPolicy Bypass -File tools\setup-web.ps1 -Enable      # allow it again and start
  powershell -ExecutionPolicy Bypass -File tools\setup-web.ps1 -Remove      # delete the task
#>
param(
  [switch]$AtStartup,
  [switch]$Stop,
  [switch]$Disable,
  [switch]$Enable,
  [switch]$Remove
)

$ErrorActionPreference = 'Stop'
$Folder = '\ZenQi\TotoChecker\'
$Name = 'Web checker'
$Root = Split-Path -Parent $PSScriptRoot
$Runner = Join-Path $PSScriptRoot 'web-service.cmd'

function Get-Task { Get-ScheduledTask -TaskPath $Folder -TaskName $Name -ErrorAction SilentlyContinue }

# Stopping the task ends its console, but the Python server it started can outlive it
# and keep the port. End whatever is listening on 127.0.0.1:8765 as well.
function Stop-Server {
  # the keep-alive loop first, or it would start the server again 10 s later
  Get-CimInstance Win32_Process -Filter "Name='cmd.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*web-service.cmd*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

if ($Remove) {
  if (Get-Task) { Stop-ScheduledTask -TaskPath $Folder -TaskName $Name -ErrorAction SilentlyContinue
                  Unregister-ScheduledTask -TaskPath $Folder -TaskName $Name -Confirm:$false }
  Stop-Server
  Write-Host 'Removed the web checker task.'
  return
}
if ($Stop -or $Disable) {
  if (-not (Get-Task)) { Write-Host 'No web checker task registered.'; return }
  Stop-ScheduledTask -TaskPath $Folder -TaskName $Name
  Stop-Server
  if ($Disable) { Disable-ScheduledTask -TaskPath $Folder -TaskName $Name | Out-Null; Write-Host 'Web checker stopped and disabled.' }
  else { Write-Host 'Web checker stopped. It starts again at the next logon or boot.' }
  return
}
if ($Enable) {
  if (-not (Get-Task)) { Write-Host 'No web checker task registered. Run without switches first.'; return }
  Enable-ScheduledTask -TaskPath $Folder -TaskName $Name | Out-Null
  Start-ScheduledTask -TaskPath $Folder -TaskName $Name
  Write-Host 'Web checker enabled and started.'
  return
}

if (-not (Test-Path $Runner)) { throw "Missing $Runner" }
if (Get-Command py -ErrorAction SilentlyContinue) { & py -3 -c "import fastapi, uvicorn" 2>$null }
else { & python -c "import fastapi, uvicorn" 2>$null }
if ($LASTEXITCODE -ne 0) {
  throw 'FastAPI is not installed. Run first:  py -3 -m pip install -r requirements.txt'
}
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'logs') | Out-Null

# Hidden console (Windows 11 conhost --headless); web-service.cmd logs to logs\web.log.
$action = New-ScheduledTaskAction -Execute 'conhost.exe' -Argument "--headless cmd.exe /c `"$Runner`"" -WorkingDirectory $Root

if ($AtStartup) {
  $trigger = New-ScheduledTaskTrigger -AtStartup
  $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType S4U -RunLevel Limited
} else {
  $trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
  $principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
}

# No time limit (it is a server); retry a failed launch up to 3 times a minute apart;
# never run two copies (the second would fail on the port anyway).
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) `
  -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
  -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# Re-running: stop the old task and any server it left behind before registering again.
if (Get-Task) { Stop-ScheduledTask -TaskPath $Folder -TaskName $Name -ErrorAction SilentlyContinue }
Stop-Server                       # also ends a copy started by hand with run-web.cmd
Start-Sleep -Seconds 1

Register-ScheduledTask -TaskPath $Folder -TaskName $Name -Action $action -Trigger $trigger -Principal $principal `
  -Settings $settings -Force `
  -Description 'TOTO/4D web checker on http://127.0.0.1:8765 (see docs\web-api.md). Ticket text is not logged.' | Out-Null

Start-ScheduledTask -TaskPath $Folder -TaskName $Name
$h = $null
foreach ($i in 1..20) {               # wait up to 20 s for it to answer
  Start-Sleep -Seconds 1
  try { $h = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -TimeoutSec 2; break } catch { }
}
if ($h) {
  Write-Host ("Web checker running: version {0}, photo reading {1}." -f $h.version, $(if ($h.photo_reading) {'on'} else {'off'}))
  # A server started from older code still answers /api/health and serves the current page
  # (the page is read from disk on every request), but routes added since then are missing.
  # 22 Oct: the install files all gave 404 that way. Check every route the app needs.
  $bad = @()
  foreach ($p in '/manifest.webmanifest', '/sw.js', '/offline.html', '/icons/icon-192.png',
                 '/icons/icon-512.png', '/icons/maskable-512.png', '/apple-touch-icon.png') {
    try { $null = Invoke-WebRequest -Uri "http://127.0.0.1:8765$p" -UseBasicParsing -TimeoutSec 3 }
    catch { $bad += $p }
  }
  if ($bad) {
    Write-Warning ("Running, but these return an error: {0}. A stale server may hold the port; run this script again, or check web\ and lottery_checker\api.py are the current versions." -f ($bad -join ', '))
  } else {
    Write-Host 'Install files OK (manifest, service worker, offline page, icons).'
  }
} else {
  Write-Warning "Registered, but http://127.0.0.1:8765 did not answer within 20 s. Check $Root\logs\web.log"
}
Write-Host ("Starts {0}. Open http://127.0.0.1:8765  Logs: {1}\logs\web.log" -f $(if ($AtStartup) {'when the PC boots'} else {'when you log on'}), $Root)
# Testing phase (higher ticket-photo limits for a limited time): show it, and prompt
# to renew or close out once it has ended. See tools\testing-phase.ps1.
& (Join-Path $PSScriptRoot 'testing-phase.ps1')
