@echo off
setlocal
cd /d "%~dp0"

py oximata.py
if errorlevel 1 (
  echo.
  echo The app did not start. Make sure Python is installed.
  pause
)
