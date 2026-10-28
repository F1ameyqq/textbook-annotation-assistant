@echo off
setlocal
set "PYTHONUTF8=1"
if exist "%~dp0runtime\customer-python.path" (
  set /p CUSTOMER_PYTHON=<"%~dp0runtime\customer-python.path"
  goto configured
)
if not exist "%~dp0.venv-customer\Scripts\python.exe" (
  echo Please run SETUP_CUSTOMER.cmd once on this computer.
  pause
  exit /b 2
)
set "CUSTOMER_PYTHON=%~dp0.venv-customer\Scripts\python.exe"
:configured
if not exist "%CUSTOMER_PYTHON%" (
  echo Configured local runtime is missing. Preserve the existing workspace.
  pause
  exit /b 2
)
"%CUSTOMER_PYTHON%" -I -B "%~dp0tools\customer.py"
if errorlevel 1 pause
