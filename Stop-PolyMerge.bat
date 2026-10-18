@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Install Python 3.11 with the Windows py launcher. See docs\LOCAL_SETUP.md.
  pause
  exit /b 1
)
py -3.11 scripts\local_demo.py stop %*
set "code=%errorlevel%"
if not "%code%"=="0" pause
exit /b %code%
