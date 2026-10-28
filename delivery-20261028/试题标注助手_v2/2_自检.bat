@echo off
title 试题标注助手 - 2 自检
cd /d "%~dp0"
echo ============================================================
echo    环境自检（只读，不写数据）
echo ============================================================
echo.
if not exist "%~dp0app\config.json" (
  echo [错误] 缺少 app\config.json，请先运行 1_安装.bat
  pause
  exit /b 1
)
set /p BOOK=书号（直接回车用配置文件里的）:
if not "%BOOK%"=="" powershell -NoProfile -Command "$p='%~dp0app\config.json'; $j=Get-Content $p -Raw -Encoding UTF8 | ConvertFrom-Json; $j.platform.fileId='%BOOK%'; $j | ConvertTo-Json -Depth 5 | ForEach-Object { [IO.File]::WriteAllText($p, $_, (New-Object Text.UTF8Encoding($false))) }"
set /p QP=题目页码（回车=34）:
if "%QP%"=="" set QP=34
set /p AP=答案页码（回车=175）:
if "%AP%"=="" set AP=175

set "CHECK_QPAGE=%QP%"
set "CHECK_APAGE=%AP%"
echo.
echo 提示：若 ego 弹"连接不是私密连接"，点 高级 - 继续前往；然后登录。只需一次。
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0app\run_ego.ps1" -Js "%~dp0app\check_env.mjs" -Out "%TEMP%\check.txt" -TimeoutSec 300
echo.
echo 看到 CHECK_ENV_OK 就绪，下一步 3_出图.bat
pause
