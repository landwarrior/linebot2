@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0package_lambda.ps1"
exit /b %ERRORLEVEL%
