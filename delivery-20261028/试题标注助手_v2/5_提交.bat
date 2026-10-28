@echo off
title 试题标注助手 - 5 提交
cd /d "%~dp0"
echo ============================================================
echo    第 5 步：提交（默认只演练，不写库）
echo ============================================================
echo.
echo 输入页面文件（pages 下的 json，不含路径），例如 p35
set /p PAGE=页面:
if not exist "%~dp0pages\%PAGE%.json" (
  echo [错误] 找不到 pages\%PAGE%.json
  pause
  exit /b 1
)
echo.
echo   1 = DRY RUN 演练（推荐）
echo   2 = 真提交（不可逆）
set /p MODE=选择（回车=1）:
if "%MODE%"=="" set MODE=1

set PYTHONIOENCODING=gbk
set "PY="
if exist "%~dp0便携PY\python.exe" set "PY=%~dp0便携PY\python.exe"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo [错误] 没有 Python
  pause
  exit /b 1
)

if "%MODE%"=="2" (
  echo.
  echo 警告：即将真实写入平台
  set /p OK=输入 YES 确认:
  if /i not "%OK%"=="YES" (
    echo 已取消
    pause
    exit /b 1
  )
  "%PY%" "%~dp0app\make_submit_runner.py" "pages\%PAGE%.json" --commit
) else (
  "%PY%" "%~dp0app\make_submit_runner.py" "pages\%PAGE%.json" --dry
)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0app\run_ego.ps1" -Js "%~dp0app\_submit_run.mjs" -Out "%TEMP%\submit.txt" -TimeoutSec 1800
echo.
echo 结果在 %TEMP%\submit.txt
pause
