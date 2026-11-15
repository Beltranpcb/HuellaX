@echo off
rem Para HuellaX en Windows. Llama a stop.ps1 sin que lo bloquee la politica de scripts.
rem Uso: stop.cmd [-Force]   (o doble clic en el Explorador)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1" %*
