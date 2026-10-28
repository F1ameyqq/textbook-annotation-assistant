@echo off
title 试题标注助手 - 4 预览
cd /d "%~dp0"
echo ============================================================
echo    第 4 步：按 spec 出「框位验收图」
echo ============================================================
echo.
echo 输入 spec 名（不含 .json），例如 p35_qspec
set /p NAME=spec:
set PYTHONIOENCODING=gbk
set "PY="
if exist "%~dp0便携PY\python.exe" set "PY=%~dp0便携PY\python.exe"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo [错误] 没有 Python，请先跑 1_安装.bat
  pause
  exit /b 1
)
echo.
"%PY%" "%~dp0app\preview_page.py" "%NAME%"
echo.
echo 检查 报告 目录下的 overlay 图：红框=题干，绿框=选项
pause
