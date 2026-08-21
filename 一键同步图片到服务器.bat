@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\sync-uploads.ps1" -Server ubuntu@ruichang.site
if errorlevel 1 pause
