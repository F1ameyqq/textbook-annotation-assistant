@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
title 试题版面测量助手

cd /d "%~dp0"

echo ============================================================
echo            试题版面测量助手   v1.0
echo ============================================================
echo.

rem ---------- 1. 找 Python ----------
set "PY="
if exist "%~dp0便携Python\python.exe" set "PY=%~dp0便携Python\python.exe"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo [错误] 没有找到 Python。
  echo        请把整个文件夹完整复制过来（不要只复制 bat 文件），
  echo        或联系技术支持安装 Python 3.11。
  echo.
  pause
  exit /b 1
)

rem ---------- 2. 临时目录重定向（必须，否则启动失败）----------
set "TMP=%~dp0tmp"
set "TEMP=%~dp0tmp"
if not exist "%~dp0tmp" mkdir "%~dp0tmp"

rem ---------- 3. 交互：页码 ----------
echo 请输入要测量的【题目页码】，例如 28-30 或 28,29,31
set /p PAGES=题目页码：
if "%PAGES%"=="" (
  echo [提示] 没有输入页码，已退出。
  pause
  exit /b 1
)

echo.
echo 如果有【答案页码】请一并输入（例如 174-176），没有就直接回车跳过
set /p APAGES=答案页码：

echo.
echo ------------------------------------------------------------
echo   即将测量：题目页 %PAGES%
if not "%APAGES%"=="" echo   答案页：%APAGES%
echo ------------------------------------------------------------
echo.

rem ---------- 4. 跑测量 ----------
if "%APAGES%"=="" (
  "%PY%" -X utf8 "%~dp0run_measure.py" --pages "%PAGES%"
) else (
  "%PY%" -X utf8 "%~dp0run_measure.py" --pages "%PAGES%" --answer-pages "%APAGES%"
)

echo.
echo ============================================================
echo   完成。请打开本文件夹下的【报告】目录：
echo     - 汇总.md       看每页测了几道题
echo     - 第N页_*.png   看框有没有框对（红色可信，橙色需重点看）
echo ============================================================
echo.
pause
