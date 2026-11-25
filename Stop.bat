@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ops\stop.ps1" %*
