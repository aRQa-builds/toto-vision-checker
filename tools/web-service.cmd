@echo off
rem Run by the "Web checker" scheduled task (tools\setup-web.ps1). Keeps the web
rem checker up: if the server stops for any reason it is started again 10 s later.
rem For a one-off run by hand use tools\run-web.cmd instead.
setlocal
cd /d "%~dp0.."
if not exist logs mkdir logs
:loop
echo [%date% %time%] starting web checker>> logs\web.log
call "%~dp0run-web.cmd" >> logs\web.log 2>&1
echo [%date% %time%] web checker stopped (exit %errorlevel%), restarting in 10 s>> logs\web.log
rem ping as a sleep: works without a keyboard, unlike timeout
ping -n 11 127.0.0.1 >nul
goto loop
