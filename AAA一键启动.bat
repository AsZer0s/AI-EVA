@echo off
chcp 65001 >nul
title AI-EVA GUI 启动器

echo.
echo ========================================
echo    AI-EVA Demo GUI 启动器
echo ========================================
echo.

:: 优先使用便携式 Python 环境
set PYTHON_EXE=python.exe
if exist "python-portable\python.exe" (
    set PYTHON_EXE=python-portable\python.exe
    echo ✅ 使用便携式 Python 环境
) else (
    :: 检查系统 Python 环境
    python --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ 错误：未找到 Python 环境
        echo.
        echo 💡 解决方案：
        echo    1. 运行 setup_python_env.bat 配置便携式 Python 环境
        echo    2. 或安装 Python 3.8+ 并添加到 PATH
        echo.
        pause
        exit /b 1
    )
    echo ✅ 使用系统 Python 环境
)

echo.

:: 检查 Web 启动器文件
if not exist "launcher_web.py" (
    echo ❌ 错误：未找到 launcher_web.py
    pause
    exit /b 1
)

:: 启动 Web GUI（不需要 tkinter）
echo 🚀 启动 Web 管理界面...
echo.
echo 📋 服务管理界面将在浏览器中打开
echo    地址: http://localhost:9000
echo.
echo 💡 提示：按 Ctrl+C 停止服务管理器
echo.

"%PYTHON_EXE%" launcher_web.py

if errorlevel 1 (
    echo.
    echo ❌ Web 启动器启动失败
    echo 💡 提示：请检查是否已安装 FastAPI 和 uvicorn
    echo    运行: pip install fastapi uvicorn[standard] websockets
    pause
)

