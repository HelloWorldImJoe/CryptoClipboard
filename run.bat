@echo off
setlocal

echo.
echo 🚀 启动 Crypto Clipboard (开发模式)
echo ==================================

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: Python 未安装或未添加到PATH
    echo 请从 https://python.org 下载并安装Python
    pause
    exit /b 1
)

REM 检查是否在项目目录
if not exist "src\main.py" (
    echo ❌ 错误: 请在项目根目录运行此脚本
    pause
    exit /b 1
)

REM 检查虚拟环境提示
if "%VIRTUAL_ENV%"=="" (
    echo ⚠️  警告: 建议创建虚拟环境
    echo    python -m venv venv
    echo    venv\Scripts\activate
    echo.
)

REM 安装依赖
echo 📦 检查依赖...
if not exist "requirements.txt" (
    echo ❌ 错误: requirements.txt 文件未找到
    pause
    exit /b 1
)

echo 🔧 安装/更新依赖...
pip install -r requirements.txt >nul 2>&1

REM 创建assets目录
if not exist "assets" (
    echo 📁 创建assets目录...
    mkdir assets
)

echo.
echo 🎯 启动应用...
echo 使用 Ctrl+C 退出
echo.

REM 启动应用
cd src
python main.py %*

pause