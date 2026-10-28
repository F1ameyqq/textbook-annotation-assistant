@echo off
title ÊÔÌâ±ê×¢ÖúÊÖ v2 - 5 Submit
cd /d "%~dp0"
echo ============================================================
echo    Step 5: submit (ego drives the real web page)
echo ============================================================
echo.
set /p PAGE=Page json name (no .json, e.g. p35):
if not exist "%~dp0pages\%PAGE%.json" (
  echo ERROR: pages\%PAGE%.json not found
  pause
  exit /b 1
)
echo.
echo   1 = DRY RUN  (structure check only, no ego needed)
echo   2 = REAL SUBMIT (needs ego + login, irreversible)
set /p MODE=Choose 1 or 2 [default 1]:
if "%MODE%"=="" set MODE=1

set "PY="
if exist "%~dp0±ãÐ¯PY\python.exe" set "PY=%~dp0±ãÐ¯PY\python.exe"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo ERROR: no Python
  pause
  exit /b 1
)
set PYTHONIOENCODING=gbk

if "%MODE%"=="2" goto REAL
goto DRY

:DRY
"%PY%" "%~dp0app\make_submit_runner.py" "pages\%PAGE%.json" --dry
echo.
echo running dry check with local node ...
set "NODE="
if exist "%~dp0±ãÐ¯NODE\node.exe" set "NODE=%~dp0±ãÐ¯NODE\node.exe"
if not defined NODE where node >nul 2>nul && set "NODE=node"
if not defined NODE (
  echo ERROR: dry run needs Node.js
  pause
  exit /b 1
)
chcp 65001 >nul
pushd "%~dp0app"
"%NODE%" _submit_run.mjs
popd
chcp 936 >nul
goto END

:REAL
echo.
echo WARNING: this will WRITE to the platform and create a new question.
set /p OK=Type YES to continue:
if /i not "%OK%"=="YES" (
  echo cancelled
  pause
  exit /b 1
)
"%PY%" "%~dp0app\make_submit_runner.py" "pages\%PAGE%.json" --commit
echo.
echo submitting via ego (do not touch the browser) ...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0app\run_ego.ps1" -Js "%~dp0app\_submit_run.mjs" -Out "%TEMP%\submit.txt" -TimeoutSec 1800
echo.
echo result: %TEMP%\submit.txt
type "%TEMP%\submit.txt"

:END
echo.
pause
