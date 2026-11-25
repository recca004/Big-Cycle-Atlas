@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ops\start.ps1" -Mode prod %*
