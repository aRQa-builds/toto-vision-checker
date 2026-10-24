@echo off
rem Refresh the Toto/4D web checker after changing any .py file (python loads routes once, at start).
rem Ends the server on 127.0.0.1:8765; the keep-alive loop (tools\web-service.cmd) starts it again ~10 s later.
rem If the loop is not running, the "Web checker" scheduled task is started instead. No admin needed.
rem Then waits for /api/health and checks the install files. Safe to run any time.
setlocal
cd /d "%~dp0"

echo [1/3] Stopping the web checker on port 8765...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }"

echo [2/3] Making sure the keep-alive task is running...
rem MultipleInstances is IgnoreNew, so this does nothing if the loop is already alive.
schtasks /run /tn "\ZenQi\TotoChecker\Web checker" >nul 2>nul

echo [3/3] Waiting for it to come back (up to 45 s)...
powershell -NoProfile -Command "$h=$null; foreach($i in 1..45){ Start-Sleep -Seconds 1; try{ $h=Invoke-RestMethod -Uri 'http://127.0.0.1:8765/api/health' -TimeoutSec 2; break }catch{} }; if(-not $h){ Write-Host 'NOT ANSWERING. Check logs\web.log, or run: powershell -ExecutionPolicy Bypass -File tools\setup-web.ps1'; exit 1 }; Write-Host ('Running: version ' + $h.version + ', photo reading ' + $(if($h.photo_reading){'on'}else{'off'})); $bad=@(); foreach($p in '/manifest.webmanifest','/sw.js','/offline.html','/icons/icon-192.png','/icons/icon-512.png','/icons/maskable-512.png','/apple-touch-icon.png'){ try{ $null=Invoke-WebRequest -Uri ('http://127.0.0.1:8765'+$p) -UseBasicParsing -TimeoutSec 3 }catch{ $bad+=$p } }; if($bad){ Write-Warning ('These return an error: ' + ($bad -join ', ')); exit 2 } else { Write-Host 'Install files OK.' }"
set RC=%errorlevel%

echo.
if %RC%==0 (echo Refresh done.) else (echo Refresh finished with a problem, code %RC%.)
echo Log tail: logs\web.log
if /i not "%~1"=="/nopause" pause
exit /b %RC%
