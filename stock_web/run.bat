@echo off
setlocal
set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT_DIR%run_windows.ps1"
set "APP_EXIT=%ERRORLEVEL%"
pause
exit /b %APP_EXIT%