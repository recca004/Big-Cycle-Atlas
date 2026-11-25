@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ops\restore-interactive.ps1" %*
