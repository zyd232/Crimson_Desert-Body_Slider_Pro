@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM =============================
REM Body Slider Pro 一键打包脚本
REM =============================

REM ========== 开关：是否在打包前安装/更新依赖 ==========
REM 1 = 运行 pip install -r requirements.txt
REM 0 = 跳过依赖安装，直接打包（依赖已齐全时使用）
set "INSTALL_DEPS=0"
REM ====================================================

REM 项目根目录（此脚本所在位置）
cd /d "%~dp0"

REM 虚拟环境路径（默认在项目根目录的 venv）
set "VENV=%~dp0venv"

if not exist "%VENV%\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found: %VENV%
    echo Run: python -m venv venv
    pause
    exit /b 1
)

call "%VENV%\Scripts\activate.bat"

if "%INSTALL_DEPS%"=="1" (
    if exist "requirements.txt" (
        echo INFO: Installing dependencies from requirements.txt...
        pip install -r requirements.txt
    ) else (
        echo WARNING: requirements.txt not found, skipping install.
    )
) else (
    echo INFO: INSTALL_DEPS=0, skipping dependency installation.
)

set "DIST_DIR=%~dp0..\release"

REM 规范化路径为绝对路径（消除 ..）
for %%I in ("%DIST_DIR%") do set "DIST_DIR=%%~fI"

echo INFO: Using Python: "%VENV%\Scripts\python.exe"
"%VENV%\Scripts\python.exe" -m PyInstaller --clean ^
    --distpath "%DIST_DIR%" ^
    PyInstaller.spec

if exist "%DIST_DIR%\Body Slider Pro.exe" (
    echo OK: Build completed.
    echo EXE: "%DIST_DIR%\Body Slider Pro.exe"
) else (
    echo FAIL: Did not find Body Slider Pro.exe. Check output above.
)

pause