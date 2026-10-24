<#
ON GRAYSKULL USE ONLY -Status. toto.zenqi.cc runs as a route on the existing
dashboard tunnel sakura-hud (see docs\web-api.md); the setup below is for a PC
without that tunnel. Kill switch there: disable the route in the dashboard.

Makes the web checker public at https://toto.zenqi.cc (P4-03) with a named
Cloudflare Tunnel, and installs cloudflared as a Windows service so the tunnel
comes back by itself after a reboot or a crash. No router port is opened: the
PC dials out to Cloudflare, and only toto.zenqi.cc reaches 127.0.0.1:8765.

Needs: an Administrator PowerShell (it installs a service), cloudflared
(winget install --id Cloudflare.cloudflared), zenqi.cc on Cloudflare (it is:
nameservers miles/ziggy), and the web checker running (tools\setup-web.ps1).

What it does, each step skipped if already done (safe to run again):
 1. cloudflared tunnel login       opens the browser once; pick zenqi.cc
 2. creates tunnel "toto-zenqi"    credentials saved as <id>.json
 3. points toto.zenqi.cc at it     a proxied CNAME in Cloudflare DNS
 4. writes C:\ProgramData\cloudflared\config.yml (and copies the credentials
    there, because the service runs as SYSTEM and cannot read your profile)
 5. installs/updates the Cloudflared service: automatic start, restarts after
    5 s, 5 s, then 60 s on failure
 6. checks https://toto.zenqi.cc/api/health and the install files

Usage (Administrator PowerShell, in the project folder):
  powershell -ExecutionPolicy Bypass -File tools\setup-tunnel.ps1           # set up or repair
  powershell -ExecutionPolicy Bypass -File tools\setup-tunnel.ps1 -Status   # service state and a live check
  powershell -ExecutionPolicy Bypass -File tools\setup-tunnel.ps1 -Stop     # take the site offline now (kill switch)
  powershell -ExecutionPolicy Bypass -File tools\setup-tunnel.ps1 -Start    # bring it back
  powershell -ExecutionPolicy Bypass -File tools\setup-tunnel.ps1 -Remove   # uninstall the service (tunnel and DNS kept)
#>
param(
  [switch]$Status,
  [switch]$Stop,
  [switch]$Start,
  [switch]$Remove,
  [switch]$Force      # replace an existing Cloudflared service that runs another config
)

$ErrorActionPreference = 'Stop'
$Tunnel   = 'toto-zenqi'
$Hostname = 'toto.zenqi.cc'
$Origin   = 'http://127.0.0.1:8765'
$Service  = 'Cloudflared'
$UserDir  = Join-Path $env:USERPROFILE '.cloudflared'
$SysDir   = Join-Path $env:ProgramData 'cloudflared'
$Config   = Join-Path $SysDir 'config.yml'
$Paths    = '/api/health', '/manifest.webmanifest', '/sw.js', '/offline.html',
            '/icons/icon-192.png', '/icons/icon-512.png', '/icons/maskable-512.png'

function Test-Site {
  # TLS 1.2 for Windows PowerShell 5.1
  [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
  $bad = @()
  foreach ($p in $Paths) {
    try { $null = Invoke-WebRequest -Uri "https://$Hostname$p" -UseBasicParsing -TimeoutSec 10 }
    catch { $bad += $p }
  }
  return ,$bad
}

if ($Status) {
  $s = Get-Service $Service -ErrorAction SilentlyContinue
  if ($s) { Write-Host "Service: $($s.Status), start type $($s.StartType)" } else { Write-Host 'Service: not installed' }
  $bad = Test-Site
  if ($bad.Count -eq 0) { Write-Host "https://$Hostname answers: page, API and install files OK." }
  else { Write-Warning ("https://$Hostname problems: {0}" -f ($bad -join ', ')) }
  return
}

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
           [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { throw 'Run this from an Administrator PowerShell (it manages a Windows service).' }

if ($Stop)  { Stop-Service $Service; Write-Host "Tunnel stopped: https://$Hostname is offline. -Start brings it back."; return }
if ($Start) { Start-Service $Service; Write-Host 'Tunnel started.'; return }

$cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
if (-not $cmd) {
  foreach ($p in "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe", "$env:ProgramFiles\cloudflared\cloudflared.exe") {
    if (Test-Path $p) { $cmd = Get-Item $p; break }
  }
}
if (-not $cmd) { throw 'cloudflared not found. Install it:  winget install --id Cloudflare.cloudflared' }
$CF = if ($cmd.Source) { $cmd.Source } else { $cmd.FullName }

# Run cloudflared; it logs to stderr, which Windows PowerShell would treat as an error.
function Invoke-CF {
  param([string[]]$Arguments, [switch]$Quiet)
  $old = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
  try {
    if ($Quiet) { $out = & $CF @Arguments 2>$null } else { $out = & $CF @Arguments 2>&1 | ForEach-Object { "$_" } }
    $code = $LASTEXITCODE
  } finally { $ErrorActionPreference = $old }
  return [pscustomobject]@{ Code = $code; Out = ($out -join "`n") }
}

if ($Remove) {
  if (Get-Service $Service -ErrorAction SilentlyContinue) {
    Stop-Service $Service -ErrorAction SilentlyContinue
    $r = Invoke-CF @('service', 'uninstall')
    if ($r.Code -ne 0) { sc.exe delete $Service | Out-Null }
  }
  Write-Host "Service removed. Tunnel '$Tunnel' and the $Hostname DNS record are kept; delete them in the Cloudflare dashboard if no longer wanted."
  return
}

# Guard: a Cloudflared service already serving something else (hud.zenqi.cc?) must not be taken over.
$existing = Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Services\$Service" -Name ImagePath -ErrorAction SilentlyContinue
if ($existing -and $existing.ImagePath -notlike "*$Config*" -and -not $Force) {
  throw ("A Cloudflared service already exists on this PC and runs something else:`n  {0}`n" +
         "It may be serving hud.zenqi.cc. Nothing was changed. Send this message to Claude, or re-run with -Force to replace it.") -f $existing.ImagePath
}

# 1. Login (cert.pem lets cloudflared manage tunnels and DNS for zenqi.cc)
if (-not (Test-Path (Join-Path $UserDir 'cert.pem'))) {
  Write-Host 'A browser window opens: sign in to Cloudflare and pick zenqi.cc, then come back here.'
  $r = Invoke-CF @('tunnel', 'login')
  if ($r.Code -ne 0 -or -not (Test-Path (Join-Path $UserDir 'cert.pem'))) { throw "Login did not finish.`n$($r.Out)" }
}

# 2. Tunnel
function Get-TunnelId {
  $r = Invoke-CF @('tunnel', 'list', '--name', $Tunnel, '--output', 'json') -Quiet
  if ($r.Code -ne 0 -or -not $r.Out) { return $null }
  # foreach unrolls the array the same way in Windows PowerShell 5.1 and PowerShell 7
  foreach ($t in ($r.Out | ConvertFrom-Json)) { if ($t.name -eq $Tunnel) { return $t.id } }
  return $null
}
$id = Get-TunnelId
if (-not $id) {
  $r = Invoke-CF @('tunnel', 'create', $Tunnel)
  if ($r.Code -ne 0) { throw "Could not create tunnel '$Tunnel'.`n$($r.Out)" }
  $id = Get-TunnelId
  if (-not $id) { throw "Tunnel '$Tunnel' was created but cannot be listed.`n$($r.Out)" }
  Write-Host "Created tunnel $Tunnel ($id)."
} else {
  Write-Host "Tunnel $Tunnel exists ($id)."
}
$cred = Join-Path $UserDir "$id.json"
if (-not (Test-Path $cred)) {
  throw "Credentials $cred are missing (tunnel made on another PC?). Delete tunnel '$Tunnel' in the Cloudflare dashboard and run this again."
}

# 3. DNS: toto.zenqi.cc -> this tunnel (overwrite so a re-created tunnel takes the name over)
$r = Invoke-CF @('tunnel', 'route', 'dns', '--overwrite-dns', $id, $Hostname)
if ($r.Code -ne 0) { throw "Could not point $Hostname at the tunnel.`n$($r.Out)" }
Write-Host "$Hostname points at the tunnel."

# 4. Config and credentials where the SYSTEM service can read them
New-Item -ItemType Directory -Force -Path $SysDir | Out-Null
$sysCred = Join-Path $SysDir "$id.json"
Copy-Item $cred $sysCred -Force
@"
# Written by tools\setup-tunnel.ps1 (P4-03). Only toto.zenqi.cc is served; anything else gets 404.
tunnel: $id
credentials-file: $sysCred
ingress:
  - hostname: $Hostname
    service: $Origin
  - service: http_status:404
"@ | Set-Content -Path $Config -Encoding ASCII
$r = Invoke-CF @('tunnel', '--config', $Config, 'ingress', 'validate')
if ($r.Code -ne 0) { throw "config.yml did not validate.`n$($r.Out)" }

# 5. Service: install once, then make it run this config, start automatically and restart on failure
if (-not (Get-Service $Service -ErrorAction SilentlyContinue)) {
  $r = Invoke-CF @('service', 'install')
  if (-not (Get-Service $Service -ErrorAction SilentlyContinue)) { throw "Service install failed.`n$($r.Out)" }
}
Stop-Service $Service -ErrorAction SilentlyContinue
$image = "`"$CF`" --config `"$Config`" tunnel run"
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\$Service" -Name ImagePath -Value $image
Set-Service $Service -StartupType Automatic
sc.exe failure $Service reset= 86400 actions= restart/5000/restart/5000/restart/60000 | Out-Null
Start-Service $Service
Write-Host 'Cloudflared service running (starts with Windows, restarts on failure).'

# 6. Live check through Cloudflare (allow up to ~60 s for the connection and DNS)
if (-not (Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue)) {
  Write-Warning 'Nothing is listening on 127.0.0.1:8765. Start the web checker: tools\setup-web.ps1'
}
$bad = $Paths
foreach ($i in 1..6) {
  Start-Sleep -Seconds 10
  $bad = Test-Site
  if ($bad.Count -eq 0) { break }
}
if ($bad.Count -eq 0) {
  Write-Host "Live: https://$Hostname (page, API and install files OK)."
} else {
  Write-Warning ("https://$Hostname not fully answering yet: {0}. Wait a minute and run with -Status. Service log: Event Viewer > Windows Logs > Application, source cloudflared." -f ($bad -join ', '))
}
