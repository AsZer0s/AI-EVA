@echo off
chcp 65001 >nul
title AI-EVA Demo 一键启动

echo.
echo ========================================
echo    AI-EVA Demo 一键启动脚本
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

:: 检查依赖
echo.
echo 📦 检查项目依赖...
if not exist "requirements.txt" (
    echo ❌ 错误：未找到 requirements.txt
    pause
    exit /b 1
)

:: 检查依赖是否已安装
echo 📦 检查依赖包...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo 📥 检测到缺少依赖，开始安装...
    pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo ❌ 依赖安装失败，请检查网络连接
        echo 💡 提示：可以使用国内镜像加速
        echo    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
        pause
        exit /b 1
    )
    echo ✅ 依赖安装完成
) else (
    echo ✅ 依赖已安装，跳过安装步骤
)

:: 检查端口占用
echo.
echo 🔍 检查服务端口...

:: 检查 IndexTTS2 端口
netstat -an | findstr ":9966" >nul
if not errorlevel 1 (
    echo ⚠️  警告：端口 9966 已被占用，IndexTTS2 服务可能无法启动
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

:: 启动 IndexTTS2 服务
echo [1/4] 启动 IndexTTS2 服务 (端口 9966)...
start "IndexTTS2" cmd /k "title IndexTTS2服务 ^& chcp 65001 ^>nul ^& cd /d %~dp0 ^&^& \"%PYTHON_EXE%\" -m uvicorn indextts_api:app --host 0.0.0.0 --port 9966 --log-level info --access-log"

:: 等待 IndexTTS2 启动
echo    等待服务启动中...
timeout /t 5 /nobreak >nul

:: 检查 IndexTTS2 是否启动成功
curl -s http://localhost:9966/ >nul 2>&1
if errorlevel 1 (
    echo    ⚠️  IndexTTS2 服务可能启动失败，请检查 IndexTTS2 窗口
) else (
    echo    ✅ IndexTTS2 服务启动成功
)

:: 启动 SenseVoice 服务
echo [2/4] 启动 SenseVoice 服务 (端口 50000)...
if exist "SenseVoice\api.py" (
    start "SenseVoice" cmd /k "title SenseVoice服务 ^& chcp 65001 ^>nul ^& cd /d %~dp0SenseVoice ^&^& \"%PYTHON_EXE%\" api.py"
    echo    等待服务启动中...
    timeout /t 5 /nobreak >nul
) else (
    echo    ⚠️  SenseVoice 服务未找到，跳过启动
    echo    💡 提示：SenseVoice 为可选服务，不影响基本功能
)

:: 启动前端服务
echo [3/4] 启动前端服务 (端口 8000)...
start "Frontend" cmd /k "title 前端服务 ^& chcp 65001 ^>nul ^& cd /d %~dp0 ^&^& \"%PYTHON_EXE%\" -m http.server 8000"

:: 等待前端启动
echo    等待服务启动中...
timeout /t 3 /nobreak >nul

:: 启动 Ollama 服务（如果可用）
echo [4/4] 检查 Ollama 服务...
ollama --version >nul 2>&1
if not errorlevel 1 (
    echo    ✅ 检测到 Ollama，启动服务 (端口 11434)...
    start "Ollama" cmd /k "title Ollama服务 ^& chcp 65001 ^>nul ^& ollama serve"
    timeout /t 3 /nobreak >nul
) else (
    echo    ⚠️  Ollama 未安装
    echo    💡 提示：Ollama 是必需服务，请先安装
    echo       下载地址：https://ollama.ai/download
    echo       安装后需要先运行: ollama pull gemma2:2b
)

echo.
echo ========================================
echo    🎉 服务启动完成！
echo ========================================
echo.
echo 📋 服务状态：
echo    • 前端界面：http://localhost:8000
echo    • IndexTTS2：http://localhost:9966
echo    • SenseVoice：http://localhost:50000
echo    • Ollama：   http://localhost:11434
echo.
echo 💡 使用提示：
echo    1. 所有服务已启动，请等待 5-10 秒让服务完全就绪
echo    2. 浏览器将自动打开，如果没有请手动访问 http://localhost:8000
echo    3. VRM 模型已自动加载（默认路径: models/default.vrm）
echo    4. 在设置面板中配置 AI 模型（需要先运行: ollama pull gemma2:2b）
echo    5. 选择音色并开始对话
echo.
echo 🔧 服务管理：
echo    • 如需停止服务，请关闭对应的命令行窗口
echo    • 所有服务窗口标题已标注，方便识别
echo    • 查看日志请查看各服务窗口的输出
echo.
echo 📝 新功能：
echo    • ✅ 改进的陪伴性对话系统
echo    • ✅ 基于音频分析的VRM口型同步
echo    • ✅ 一键启动所有服务
echo.

:: 自动打开浏览器
timeout /t 5 /nobreak >nul
echo 🌐 正在打开浏览器...
start http://localhost:8000

echo.
echo 按任意键退出...
pause >nul
