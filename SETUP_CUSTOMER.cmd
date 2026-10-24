@echo off
setlocal
set "PYTHONUTF8=1"
if exist "%~dp0.venv-customer" (
  echo Existing runtime retained. Setup will not replace it.
  pause
  exit /b 2
)
py -3.12 -m venv "%~dp0.venv-customer"
if errorlevel 1 goto failed
"%~dp0.venv-customer\Scripts\python.exe" -m pip install -r "%~dp0requirements-customer.txt"
if errorlevel 1 goto failed
echo Setup finished. Open START_CUSTOMER.cmd.
pause
exit /b 0
:failed
echo Setup stopped. Preserve this runtime and error output; no automatic retry.
pause
exit /b 2
