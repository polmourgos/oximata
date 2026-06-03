@echo off
setlocal
cd /d "%~dp0"

echo Building Oximata.exe...
echo.

py -m pip install -r requirements.txt
if errorlevel 1 goto error

py -m pip install -r requirements-build.txt
if errorlevel 1 goto error

py -m PyInstaller --clean --noconfirm Oximata.spec
if errorlevel 1 goto error

echo.
echo Done.
echo The executable is here:
echo %~dp0dist\Oximata.exe
echo.
pause
exit /b 0

:error
echo.
echo Build failed. Check the messages above.
pause
exit /b 1
