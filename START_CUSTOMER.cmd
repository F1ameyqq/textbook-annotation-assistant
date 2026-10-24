@echo off
setlocal
set "PYTHONUTF8=1"
if not exist "%~dp0.venv-customer\Scripts\python.exe" (
  echo Please run SETUP_CUSTOMER.cmd once on this computer.
  pause
  exit /b 2
)
"%~dp0.venv-customer\Scripts\python.exe" -I -B "%~dp0tools\customer.py"
if errorlevel 1 pause
