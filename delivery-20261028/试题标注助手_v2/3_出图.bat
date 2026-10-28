@echo off
title 试题标注助手 - 3 出图
cd /d "%~dp0"
echo ============================================================
echo    第 3 步：出「行号图」+ spec 模板（不需要登录）
echo ============================================================
echo.
echo 输入题目页码，支持 35 / 35,36 / 35-37
set /p PAGES=页码:
if "%PAGES%"=="" (
  echo 没有输入
  pause
  exit /b 1
)
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
"%PY%" "%~dp0app\make_assets.py" %PAGES%
echo.
echo 打开 报告\pNN_rows.png 看行号，编辑 specs\pNN_qspec.json 后运行 4_预览.bat
pause
