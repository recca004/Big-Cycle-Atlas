@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ops\export_research.ps1" %*
