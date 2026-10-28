@echo off
title 试题标注助手 - 1 安装
cd /d "%~dp0"
echo ============================================================
echo    试题标注助手 . 安装（只需运行一次）
echo ============================================================
echo.
set "PY="
set "NODE="
set "EGO="

if exist "%~dp0便携PY\python.exe" set "PY=%~dp0便携PY\python.exe"
if not defined PY where python >nul 2>nul && set "PY=python"
echo [1/5] Python
if defined PY (
  "%PY%" --version
) else (
  echo       [缺失] 没有找到 Python 3
  echo       请装 Python 3.11，或把便携版放到 便携PY 文件夹
)
echo.

if defined PY (
  echo [2/5] Python 依赖 numpy / Pillow / opencv
  "%PY%" -c "import numpy, PIL, cv2" >nul 2>nul
  if errorlevel 1 (
    echo       安装中，需要联网约 60MB ...
    "%PY%" -m pip install numpy pillow opencv-python
  ) else (
    echo       OK
  )
)
echo.

if exist "%~dp0便携NODE\node.exe" set "NODE=%~dp0便携NODE\node.exe"
if not defined NODE where node >nul 2>nul && set "NODE=node"
echo [3/5] Node.js
if defined NODE (
  "%NODE%" --version
) else (
  echo       [缺失] 需要 Node.js 18 以上，请从 nodejs.org 装 LTS 版
)
echo.

echo [4/5] ego lite（只有提交步骤需要）
if exist "%USERPROFILE%\.local\share\ego\active_version_dir\ego-browser.exe" (
  set "EGO=%USERPROFILE%\.local\share\ego\active_version_dir\ego-browser.exe"
)
if not defined EGO where ego-browser >nul 2>nul && set "EGO=ego-browser"
if defined EGO (
  echo       已安装
) else (
  echo       未安装。可跳过（不影响 出图/预览，只影响提交）
  set /p CRX=请输入 ego 安装包 .crx3 的完整路径，直接回车跳过:
  if defined CRX (
    if exist "%CRX%" (
      powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0app\install\install_ego.ps1" -Crx "%CRX%"
    ) else (
      echo       [错误] 文件不存在
    )
  )
)
echo.

echo [5/5] 配置文件
if exist "%~dp0app\config.json" (
  echo       已存在
) else (
  copy "%~dp0app\config.example.json" "%~dp0app\config.json" >nul
  echo       已创建 app\config.json，请把 platform.fileId 改成书号
)
echo.
echo ============================================================
echo   检查完毕。下一步运行 2_自检.bat
echo ============================================================
pause
