@echo off
setlocal
cd /d "%~dp0app"
call npm run dev -- --host 127.0.0.1
pause
