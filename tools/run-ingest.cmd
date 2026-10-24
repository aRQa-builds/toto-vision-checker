@echo off
rem After-draw results capture for one game. Usage: run-ingest.cmd 4d  |  run-ingest.cmd toto  |  run-ingest.cmd toto --catch-up
rem Kill switch: set TOTO_INGEST_ENABLED=0 below (or run setup-schedule.ps1 -Disable).
setlocal
cd /d "%~dp0.."
set TOTO_INGEST_ENABLED=1
set TOTO_CONTACT=ralph@arqas.io
rem Switch TOTO_CONTACT back to results@zenqi.cc once that mailbox exists and is read (P2-05).
if not exist logs mkdir logs
echo [%date% %time%] run %*>> logs\ingest.log
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m lottery_checker.ingest %* >> logs\ingest.log 2>&1
) else (
  python -m lottery_checker.ingest %* >> logs\ingest.log 2>&1
)
exit /b %errorlevel%
