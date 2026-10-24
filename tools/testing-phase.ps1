<#
Testing phase for the web checker: higher ticket-photo limits for a limited time
(owner's rule, 22 Oct 2026). Writes data\testing_phase.json; the server reads it on
every request, so nothing needs restarting.

  Normal:  20 ticket photos per person an hour, 150 a day for the whole site.
  Testing: 200 an hour, 1000 a day (env TOTO_TESTING_PER_HOUR / TOTO_TESTING_PER_DAY).
  Official-result screenshots have no per-person limit either way.

When the phase runs out, the normal limits come back by themselves. The site shows
a banner while testing (and "renew or close out" on the last day), and
setup-web.ps1 prints the state, so the owner is prompted to decide.

Usage (PowerShell, in the project folder):
  powershell -ExecutionPolicy Bypass -File tools\testing-phase.ps1 -Start            # open for 7 days
  powershell -ExecutionPolicy Bypass -File tools\testing-phase.ps1 -Start -Days 3    # or another length
  powershell -ExecutionPolicy Bypass -File tools\testing-phase.ps1 -Renew            # 7 more days from now
  powershell -ExecutionPolicy Bypass -File tools\testing-phase.ps1 -End              # close out for deployment
  powershell -ExecutionPolicy Bypass -File tools\testing-phase.ps1                   # show the state
#>
param(
  [switch]$Start,
  [switch]$Renew,
  [switch]$End,
  [int]$Days = 7
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$File = Join-Path $Root 'data\testing_phase.json'

function Get-Phase {
  if (-not (Test-Path $File)) { return $null }
  try { return Get-Content $File -Raw | ConvertFrom-Json } catch { return $null }
}

function Write-Phase([datetime]$started, [datetime]$ends, [int]$renewals) {
  New-Item -ItemType Directory -Force -Path (Split-Path $File) | Out-Null
  $rec = [ordered]@{
    started  = $started.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss'Z'")
    ends     = $ends.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss'Z'")
    renewals = $renewals
    note     = 'Testing phase: higher ticket-photo limits. tools\testing-phase.ps1 -Renew or -End.'
  }
  # UTF-8 without BOM so any reader takes it
  [IO.File]::WriteAllText($File, ($rec | ConvertTo-Json), (New-Object System.Text.UTF8Encoding $false))
}

function Show-Phase {
  $p = Get-Phase
  if (-not $p) { Write-Host 'No testing phase: normal limits (deployment mode).'; return }
  $ends = ([datetime]$p.ends).ToLocalTime()
  $left = ($ends - (Get-Date)).TotalDays
  if ($left -gt 0) {
    Write-Host ("Testing phase ON until {0:ddd d MMM yyyy HH:mm} ({1:N1} days left). Higher ticket-photo limits." -f $ends, $left)
    if ($left -le 1) { Write-Warning 'Last day: renew (-Renew) or close out for deployment (-End).' }
  } else {
    Write-Warning ("Testing phase ENDED {0:ddd d MMM yyyy HH:mm}; normal limits are back." -f $ends)
    Write-Host '  Renew for 7 more days:   powershell -ExecutionPolicy Bypass -File tools\testing-phase.ps1 -Renew'
    Write-Host '  Close out for deployment: powershell -ExecutionPolicy Bypass -File tools\testing-phase.ps1 -End'
  }
}

if ($End) {
  if (Test-Path $File) { Remove-Item $File -Force }
  Write-Host 'Testing phase closed out. Normal limits from now on (deployment mode).'
  return
}
if ($Start -or $Renew) {
  if ($Days -lt 1 -or $Days -gt 30) { throw 'Days must be 1 to 30.' }
  $now = Get-Date
  $p = Get-Phase
  $started = if ($Renew -and $p) { [datetime]$p.started } else { $now }
  $renewals = if ($Renew -and $p) { [int]$p.renewals + 1 } else { 0 }
  if ($Renew -and -not $p) { Write-Host 'No testing phase to renew, so starting one.' }
  Write-Phase $started $now.AddDays($Days) $renewals
}
Show-Phase
