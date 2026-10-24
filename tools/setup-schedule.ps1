<#
Registers the after-draw capture as Windows scheduled tasks (Windows 11).

Times are LOCAL time: Grayskull's clock must be on Singapore time (UTC+08:00).
  4D   : Wed, Sat, Sun 18:45 and 19:00 retry
  TOTO : Mon, Thu      21:45 and 22:00 retry
  TOTO : Fri           21:45 and 22:00 catch-up (special draws: New Year, Reunion,
                       Hong Bao, National Day replace that week's Thursday draw)
The retry makes no request if the draw is already stored. The Friday catch-up makes
no request on a normal week, because Thursday's draw is already stored.

Usage (PowerShell, in the project folder, no admin needed):
  powershell -ExecutionPolicy Bypass -File tools\setup-schedule.ps1            # create or update
  powershell -ExecutionPolicy Bypass -File tools\setup-schedule.ps1 -Disable   # kill switch: pause all
  powershell -ExecutionPolicy Bypass -File tools\setup-schedule.ps1 -Enable    # resume
  powershell -ExecutionPolicy Bypass -File tools\setup-schedule.ps1 -Remove    # delete the tasks
#>
param(
  [switch]$Disable,
  [switch]$Enable,
  [switch]$Remove
)

$ErrorActionPreference = 'Stop'
$Folder = '\ZenQi\TotoChecker\'
$Root = Split-Path -Parent $PSScriptRoot
$Runner = Join-Path $PSScriptRoot 'run-ingest.cmd'

$Tasks = @(
  @{ Name = '4D capture';        Game = '4d';   Days = 'Wednesday','Saturday','Sunday'; At = '18:45' },
  @{ Name = '4D capture retry';  Game = '4d';   Days = 'Wednesday','Saturday','Sunday'; At = '19:00' },
  @{ Name = 'TOTO capture';      Game = 'toto'; Days = 'Monday','Thursday';             At = '21:45' },
  @{ Name = 'TOTO capture retry';Game = 'toto'; Days = 'Monday','Thursday';             At = '22:00' },
  @{ Name = 'TOTO Friday catch-up';       Game = 'toto --catch-up'; Days = 'Friday'; At = '21:45' },
  @{ Name = 'TOTO Friday catch-up retry'; Game = 'toto --catch-up'; Days = 'Friday'; At = '22:00' }
)

if ($Remove) {
  foreach ($t in $Tasks) { Unregister-ScheduledTask -TaskPath $Folder -TaskName $t.Name -Confirm:$false -ErrorAction SilentlyContinue }
  Write-Host 'Removed TOTO checker tasks.'
  return
}
if ($Disable) {
  foreach ($t in $Tasks) { Disable-ScheduledTask -TaskPath $Folder -TaskName $t.Name | Out-Null }
  Write-Host 'Kill switch ON: all capture tasks disabled. The app falls back to the screenshot flow.'
  return
}
if ($Enable) {
  foreach ($t in $Tasks) { Enable-ScheduledTask -TaskPath $Folder -TaskName $t.Name | Out-Null }
  Write-Host 'Capture tasks enabled.'
  return
}

$tz = (Get-TimeZone).BaseUtcOffset
if ($tz -ne [TimeSpan]::FromHours(8)) {
  Write-Warning "This PC is on UTC$($tz.ToString()) not UTC+08:00. Task times are local, so set the time zone to Singapore first."
}
if (-not (Test-Path $Runner)) { throw "Missing $Runner" }

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
  -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

foreach ($t in $Tasks) {
  $action  = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument "/c `"$Runner`" $($t.Game)" -WorkingDirectory $Root
  $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $t.Days -At $t.At
  Register-ScheduledTask -TaskPath $Folder -TaskName $t.Name -Action $action -Trigger $trigger -Settings $settings `
    -Description 'After-draw capture of the official result (one request, credited to Singapore Pools). See docs\ingest-schedule.md.' `
    -Force | Out-Null
  Write-Host ("Registered {0,-20} {1} at {2}" -f $t.Name, ($t.Days -join ','), $t.At)
}
Write-Host "Done. Logs: $Root\logs\ingest.log   Data: $Root\data\"
