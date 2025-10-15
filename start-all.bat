@echo off
chcp 65001 >nul
title AI-EVA Demo 一键启动

echo.
echo ========================================
echo    AI-EVA Demo 一键启动脚本
echo ========================================
echo.

:: 检查 Python 环境
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误：未找到 Python 环境
    echo 请先安装 Python 3.8+ 并添加到 PATH
    pause
    exit /b 1
)

echo ✅ Python 环境检查通过

:: 检查依赖
echo.
echo 📦 检查项目依赖...
if not exist "requirements.txt" (
    echo ❌ 错误：未找到 requirements.txt
    pause
    exit /b 1
)

:: 安装依赖（如果需要）
echo 📥 安装/更新依赖包...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ❌ 依赖安装失败，请检查网络连接
    pause
    exit /b 1
)

echo ✅ 依赖安装完成

:: 检查端口占用
echo.
echo 🔍 检查服务端口...

:: 检查 ChatTTS 端口
netstat -an | findstr ":9966" >nul
if not errorlevel 1 (
    echo ⚠️  警告：端口 9966 已被占用，ChatTTS 服务可能无法启动
)

:: 检查 SenseVoice 端口
netstat -an | findstr ":50000" >nul
if not errorlevel 1 (
    echo ⚠️  警告：端口 50000 已被占用，SenseVoice 服务可能无法启动
)

:: 检查 Ollama 端口
netstat -an | findstr ":11434" >nul
if not errorlevel 1 (
    echo ⚠️  警告：端口 11434 已被占用，Ollama 服务可能无法启动
)

:: 检查前端端口
netstat -an | findstr ":8000" >nul
if not errorlevel 1 (
    echo ⚠️  警告：端口 8000 已被占用，前端服务可能无法启动
)

echo.
echo 🚀 启动服务中...
echo.

:: 创建日志目录
if not exist "logs" mkdir logs

:: 启动 ChatTTS 服务
echo [1/4] 启动 ChatTTS 服务 (端口 9966)...
start "ChatTTS" cmd /k "uvicorn chattts_api:app --host 0.0.0.0 --port 9966"

:: 等待 ChatTTS 启动
timeout /t 3 /nobreak >nul

:: 启动 SenseVoice 服务
echo [2/4] 启动 SenseVoice 服务 (端口 50000)...
if exist "SenseVoice\api.py" (
    start "SenseVoice" cmd /k "cd SenseVoice && python api.py"
) else (
    echo ⚠️  SenseVoice 服务未找到，跳过启动
)

:: 等待 SenseVoice 启动
timeout /t 3 /nobreak >nul

:: 启动前端服务
echo [3/4] 启动前端服务 (端口 8000)...
start "Frontend" cmd /k "python -m http.server 8000"

:: 等待前端启动
timeout /t 2 /nobreak >nul

:: 启动 Ollama 服务（如果可用）
echo [4/4] 检查 Ollama 服务...
ollama --version >nul 2>&1
if not errorlevel 1 (
    echo ✅ 启动 Ollama 服务 (端口 11434)...
    start "Ollama" cmd /k "ollama serve"
) else (
    echo ⚠️  Ollama 未安装，请手动安装并启动
    echo    下载地址：https://ollama.ai/download
)

echo.
echo ========================================
echo    🎉 服务启动完成！
echo ========================================
echo.
echo 📋 服务状态：
echo    • 前端界面：http://localhost:8000
echo    • ChatTTS：  http://localhost:9966
echo    • SenseVoice：http://localhost:50000
echo    • Ollama：   http://localhost:11434
echo.
echo 💡 使用提示：
echo    1. 等待 10-15 秒让所有服务完全启动
echo    2. 在浏览器中打开 http://localhost:8000
echo    3. 上传 VRM 模型文件开始体验
echo    4. 在设置面板中配置 AI 模型和音色
echo.
echo 🔧 如需停止服务，请关闭对应的命令行窗口
echo.

:: 自动打开浏览器
timeout /t 5 /nobreak >nul
echo 🌐 正在打开浏览器...
start http://localhost:8000

echo.
echo 按任意键退出...
pause >nul
