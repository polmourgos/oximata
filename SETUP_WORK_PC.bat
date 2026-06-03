@echo off
setlocal
cd /d "%~dp0"

call "%~dp0BUILD_EXE.bat"
if errorlevel 1 exit /b 1

call "%~dp0CREATE_DESKTOP_SHORTCUT.bat"
