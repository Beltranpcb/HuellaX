@echo off
rem Arranca HuellaX en Windows. Llama a start.ps1 sin que lo bloquee la politica de scripts.
rem Uso: start.cmd [-NoOptional] [-NoBrowser]   (o doble clic en el Explorador)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
set "RC=%errorlevel%"
if not "%RC%"=="0" (
  echo.
  pause
)
exit /b %RC%
