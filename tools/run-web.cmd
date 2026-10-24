@echo off
rem Web checker (P4-02). Serves http://127.0.0.1:8765 for the tunnel to reach.
rem Stop with Ctrl+C. Ticket text is not stored or logged.
setlocal
cd /d "%~dp0.."
set TOTO_WEB_HOST=127.0.0.1
set TOTO_WEB_PORT=8765
rem Photo/screenshot reading stays off until a key is set (P3-01):
rem set GOOGLE_VISION_API_KEY=...
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m lottery_checker.api
) else (
  python -m lottery_checker.api
)
