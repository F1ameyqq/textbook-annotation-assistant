@echo off
title ÊÔÌâ±ê×¢ÖúÊÖ v2 - 1 Install
cd /d "%~dp0"
echo ============================================================
echo    Install (run once)
echo    ego lite is REQUIRED for the submit step (A-based chain)
echo ============================================================
echo.
set "PY="
set "NODE="
set "EGO="

if exist "%~dp0±ãÐ¯PY\python.exe" set "PY=%~dp0±ãÐ¯PY\python.exe"
if not defined PY where python >nul 2>nul && set "PY=python"
echo [1/5] Python (required: measure / preview / coords)
if defined PY (
  "%PY%" --version
) else (
  echo       MISSING Python 3.11 - install it, or put portable python in ±ãÐ¯PY\
)
echo.

if defined PY (
  echo [2/5] Python packages: numpy / Pillow / opencv
  "%PY%" -c "import numpy, PIL, cv2" >nul 2>nul
  if errorlevel 1 (
    echo       installing, needs network ~60MB ...
    "%PY%" -m pip install numpy pillow opencv-python
  ) else (
    echo       OK
  )
)
echo.

if exist "%~dp0±ãÐ¯NODE\node.exe" set "NODE=%~dp0±ãÐ¯NODE\node.exe"
if not defined NODE where node >nul 2>nul && set "NODE=node"
echo [3/5] Node.js (required: dry run + submit)
if defined NODE (
  "%NODE%" --version
) else (
  echo       MISSING Node.js 18+ - install LTS from nodejs.org
)
echo.

echo [4/5] ego lite (REQUIRED for submit)
if exist "%USERPROFILE%\.local\share\ego\active_version_dir\ego-browser.exe" (
  set "EGO=%USERPROFILE%\.local\share\ego\active_version_dir\ego-browser.exe"
)
if not defined EGO where ego-browser >nul 2>nul && set "EGO=ego-browser"
if defined EGO (
  echo       already installed:
  "%EGO%" --version
) else (
  echo       NOT installed.
  set /p CRX=Input full path of ego-*.crx3 then Enter:
  if defined CRX (
    if exist "%CRX%" (
      powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0app\install\install_ego.ps1" -Crx "%CRX%"
    ) else (
      echo       ERROR: file not found
    )
  ) else (
    echo       skipped - submit will NOT work without ego
  )
)
echo.

echo.
echo [5/5] config
if exist "%~dp0app\config.json" (
  echo       exists

  copy "%~dp0app\config.example.json" "%~dp0app\config.json" >nul
  echo       created app\config.json - set platform.fileId to your book id
)
echo.
if defined EGO (
  if exist "%~dp0app\config.json" (
    powershell -NoProfile -Command "$p='%~dp0app\config.json'; $j=Get-Content $p -Raw -Encoding UTF8 | ConvertFrom-Json; $j.paths.egoExe='%EGO%'; $j | ConvertTo-Json -Depth 5 | ForEach-Object { [IO.File]::WriteAllText($p, $_, (New-Object Text.UTF8Encoding($false))) }"
    echo       ego path written into config.json
  )
)
echo.
echo ============================================================
echo   Next: run 2_check.bat  (first login + cert click)
echo ============================================================
pause