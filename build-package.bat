@echo off
chcp 65001 >nul
title AI-EVA 打包工具

echo.
echo ========================================
echo    AI-EVA Demo 打包工具
echo ========================================
echo.

set PACKAGE_NAME=AI-EVA-Demo
set PACKAGE_DIR=%PACKAGE_NAME%

:: 创建打包目录
if exist "%PACKAGE_DIR%" (
    echo 清理旧的打包目录...
    rmdir /s /q "%PACKAGE_DIR%"
)
mkdir "%PACKAGE_DIR%"
mkdir "%PACKAGE_DIR%\models"
mkdir "%PACKAGE_DIR%\logs"

echo ✅ 创建打包目录完成

:: 复制必要文件
echo.
echo 📦 复制项目文件...
copy /Y index.html "%PACKAGE_DIR%\"
copy /Y config.py "%PACKAGE_DIR%\"
copy /Y chattts_api.py "%PACKAGE_DIR%\"
copy /Y sensevoice_api.py "%PACKAGE_DIR%\"
copy /Y requirements.txt "%PACKAGE_DIR%\"
copy /Y requirements-gpu.txt "%PACKAGE_DIR%\"
copy /Y README.md "%PACKAGE_DIR%\"
copy /Y start-all.bat "%PACKAGE_DIR%\"

:: 复制目录
xcopy /E /I /Y utils "%PACKAGE_DIR%\utils"
xcopy /E /I /Y SenseVoice "%PACKAGE_DIR%\SenseVoice"

echo ✅ 文件复制完成

:: 创建启动脚本
echo.
echo 📝 创建一键启动脚本...
(
echo @echo off
echo chcp 65001 ^>nul
echo title AI-EVA Demo 一键启动
echo.
echo echo ========================================
echo echo    AI-EVA Demo 一键启动
echo echo ========================================
echo echo.
echo.
echo :: 检查 Python 环境
echo python --version ^>nul 2^>^&1
echo if errorlevel 1 ^(
echo     echo ❌ 错误：未找到 Python 环境
echo     echo 请先安装 Python 3.8+ 并添加到 PATH
echo     pause
echo     exit /b 1
echo ^)
echo.
echo echo ✅ Python 环境检查通过
echo.
echo :: 检查依赖
echo echo.
echo echo 📦 检查项目依赖...
echo if not exist "requirements.txt" ^(
echo     echo ❌ 错误：未找到 requirements.txt
echo     pause
echo     exit /b 1
echo ^)
echo.
echo :: 安装依赖（如果需要）
echo echo 📥 安装/更新依赖包...
echo pip install -r requirements.txt --quiet
echo if errorlevel 1 ^(
echo     echo ❌ 依赖安装失败，请检查网络连接
echo     pause
echo     exit /b 1
echo ^)
echo.
echo echo ✅ 依赖安装完成
echo.
echo :: 检查端口占用
echo echo.
echo echo 🔍 检查服务端口...
echo.
echo :: 检查 ChatTTS 端口
echo netstat -an ^| findstr ":9966" ^>nul
echo if not errorlevel 1 ^(
echo     echo ⚠️  警告：端口 9966 已被占用，ChatTTS 服务可能无法启动
echo ^)
echo.
echo :: 检查 SenseVoice 端口
echo netstat -an ^| findstr ":50000" ^>nul
echo if not errorlevel 1 ^(
echo     echo ⚠️  警告：端口 50000 已被占用，SenseVoice 服务可能无法启动
echo ^)
echo.
echo :: 检查 Ollama 端口
echo netstat -an ^| findstr ":11434" ^>nul
echo if not errorlevel 1 ^(
echo     echo ⚠️  警告：端口 11434 已被占用，Ollama 服务可能无法启动
echo ^)
echo.
echo :: 检查前端端口
echo netstat -an ^| findstr ":8000" ^>nul
echo if not errorlevel 1 ^(
echo     echo ⚠️  警告：端口 8000 已被占用，前端服务可能无法启动
echo ^)
echo.
echo echo.
echo echo 🚀 启动服务中...
echo echo.
echo.
echo :: 创建日志目录
echo if not exist "logs" mkdir logs
echo.
echo :: 启动 ChatTTS 服务
echo echo [1/4] 启动 ChatTTS 服务 ^(端口 9966^)...
echo start "ChatTTS" cmd /k "uvicorn chattts_api:app --host 0.0.0.0 --port 9966"
echo.
echo :: 等待 ChatTTS 启动
echo timeout /t 3 /nobreak ^>nul
echo.
echo :: 启动 SenseVoice 服务
echo echo [2/4] 启动 SenseVoice 服务 ^(端口 50000^)...
echo if exist "SenseVoice\api.py" ^(
echo     start "SenseVoice" cmd /k "cd SenseVoice ^&^& python api.py"
echo ^) else ^(
echo     echo ⚠️  SenseVoice 服务未找到，跳过启动
echo ^)
echo.
echo :: 等待 SenseVoice 启动
echo timeout /t 3 /nobreak ^>nul
echo.
echo :: 启动前端服务
echo echo [3/4] 启动前端服务 ^(端口 8000^)...
echo start "Frontend" cmd /k "python -m http.server 8000"
echo.
echo :: 等待前端启动
echo timeout /t 2 /nobreak ^>nul
echo.
echo :: 启动 Ollama 服务（如果可用）
echo echo [4/4] 检查 Ollama 服务...
echo ollama --version ^>nul 2^>^&1
echo if not errorlevel 1 ^(
echo     echo ✅ 启动 Ollama 服务 ^(端口 11434^)...
echo     start "Ollama" cmd /k "ollama serve"
echo ^) else ^(
echo     echo ⚠️  Ollama 未安装，请手动安装并启动
echo     echo    下载地址：https://ollama.ai/download
echo ^)
echo.
echo echo.
echo echo ========================================
echo echo    🎉 服务启动完成！
echo echo ========================================
echo echo.
echo echo 📋 服务状态：
echo echo    • 前端界面：http://localhost:8000
echo echo    • ChatTTS：  http://localhost:9966
echo echo    • SenseVoice：http://localhost:50000
echo echo    • Ollama：   http://localhost:11434
echo echo.
echo echo 💡 使用提示：
echo echo    1. 等待 10-15 秒让所有服务完全启动
echo echo    2. 在浏览器中打开 http://localhost:8000
echo echo    3. 上传 VRM 模型文件开始体验
echo echo    4. 在设置面板中配置 AI 模型和音色
echo echo.
echo echo 🔧 如需停止服务，请关闭对应的命令行窗口
echo echo.
echo.
echo :: 自动打开浏览器
echo timeout /t 5 /nobreak ^>nul
echo echo 🌐 正在打开浏览器...
echo start http://localhost:8000
echo.
echo echo.
echo echo 按任意键退出...
echo pause ^>nul
) > "%PACKAGE_DIR%\启动.bat"

echo ✅ 启动脚本创建完成

:: 创建使用说明
echo.
echo 📖 创建使用说明...
(
echo # AI-EVA Demo 使用说明
echo.
echo ## 快速开始
echo.
echo 1. 双击运行 `启动.bat` 文件
echo 2. 等待所有服务启动完成（约10-15秒）
echo 3. 浏览器会自动打开，如果没有自动打开，请手动访问 http://localhost:8000
echo 4. 上传 VRM 模型文件开始体验
echo.
echo ## 环境要求
echo.
echo - Python 3.8+
echo - 8GB+ 内存（推荐16GB）
echo - 现代浏览器（Chrome/Firefox/Edge）
echo.
echo ## 首次使用
echo.
echo 1. 确保已安装 Python 3.8+
echo 2. 确保已安装 Ollama（下载地址：https://ollama.ai/download）
echo 3. 运行启动脚本，会自动安装依赖
echo 4. 等待服务启动后，在浏览器中上传 VRM 模型
echo.
echo ## 注意事项
echo.
echo - 首次运行会自动安装依赖，需要网络连接
echo - 确保端口 8000、9966、50000、11434 未被占用
echo - VRM 模型文件需要用户自行准备
echo.
echo ## 功能特性
echo.
echo - ✅ 智能对话（基于 Ollama）
echo - ✅ 语音合成（ChatTTS）
echo - ✅ 语音识别（SenseVoice）
echo - ✅ VRM 3D 角色展示
echo - ✅ 口型同步
echo - ✅ 情感表达
echo.
echo 更多信息请查看 README.md
) > "%PACKAGE_DIR%\使用说明.txt"

echo ✅ 使用说明创建完成

:: 创建压缩包（如果存在7z或WinRAR）
echo.
echo 📦 创建压缩包...
where 7z >nul 2>&1
if %errorlevel% == 0 (
    echo 使用 7-Zip 创建压缩包...
    7z a -tzip "%PACKAGE_NAME%.zip" "%PACKAGE_DIR%\*" -r
    echo ✅ 压缩包创建完成: %PACKAGE_NAME%.zip
) else (
    where winrar >nul 2>&1
    if %errorlevel% == 0 (
        echo 使用 WinRAR 创建压缩包...
        winrar a -afzip "%PACKAGE_NAME%.zip" "%PACKAGE_DIR%\*"
        echo ✅ 压缩包创建完成: %PACKAGE_NAME%.zip
    ) else (
        echo ⚠️  未找到压缩工具，请手动压缩 %PACKAGE_DIR% 目录
    )
)

echo.
echo ========================================
echo    ✅ 打包完成！
echo ========================================
echo.
echo 📦 打包目录: %PACKAGE_DIR%
echo 📝 启动脚本: %PACKAGE_DIR%\启动.bat
echo.
echo 💡 提示：
echo    1. 可以将 %PACKAGE_DIR% 目录复制到任何位置使用
echo    2. 双击 启动.bat 即可一键启动所有服务
echo    3. 首次运行会自动安装依赖
echo.
pause

