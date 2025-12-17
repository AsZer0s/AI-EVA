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
copy /Y ai_eva_launcher.py "%PACKAGE_DIR%\"
if exist "启动GUI.bat" copy /Y "启动GUI.bat" "%PACKAGE_DIR%\"
if exist "setup_python_env.bat" copy /Y "setup_python_env.bat" "%PACKAGE_DIR%\"

:: 复制目录
xcopy /E /I /Y utils "%PACKAGE_DIR%\utils"
xcopy /E /I /Y SenseVoice "%PACKAGE_DIR%\SenseVoice"

:: 复制 Python 便携式环境（如果存在）
if exist "python-portable" (
    echo 📦 复制 Python 便携式环境...
    xcopy /E /I /Y python-portable "%PACKAGE_DIR%\python-portable"
    echo ✅ Python 环境已包含在打包中
) else (
    echo ⚠️  未找到 python-portable 目录
    echo 💡 提示：运行 setup_python_env.bat 配置 Python 环境后再打包
)

echo ✅ 文件复制完成

:: 创建启动脚本（直接复制现有文件）
echo.
echo 📝 创建一键启动脚本...
if exist "start-all.bat" (
    copy /Y "start-all.bat" "%PACKAGE_DIR%\启动.bat" >nul
    echo ✅ 启动脚本创建完成（从 start-all.bat 复制）
) else (
    echo ⚠️  警告：未找到 start-all.bat，将创建简化版启动脚本
    (
        echo @echo off
        echo chcp 65001 ^>nul
        echo title AI-EVA Demo
        echo python -m http.server 8000
    ) > "%PACKAGE_DIR%\启动.bat"
)

:: 创建使用说明（使用 PowerShell 确保 UTF-8 编码）
echo.
echo 📖 创建使用说明...
powershell -Command "[System.IO.File]::WriteAllText('%PACKAGE_DIR%\使用说明.txt', @'
# AI-EVA Demo 使用说明

## 快速开始

1. 双击运行 `启动.bat` 文件
2. 等待所有服务启动完成（约10-15秒）
3. 浏览器会自动打开，如果没有自动打开，请手动访问 http://localhost:8000
4. VRM 模型已自动加载（默认路径: models/default.vrm）

## 环境要求

- Python 3.8+
- 8GB+ 内存（推荐16GB）
- 现代浏览器（Chrome/Firefox/Edge）

## 首次使用

1. 确保已安装 Python 3.8+
2. 确保已安装 Ollama（下载地址：https://ollama.ai/download）
3. 运行启动脚本，会自动安装依赖
4. 等待服务启动后，VRM 模型会自动加载（请确保 models/default.vrm 文件存在）

## 注意事项

- 首次运行会自动安装依赖，需要网络连接
- 确保端口 8000、9966、50000、11434 未被占用
- VRM 模型文件需要用户自行准备

## 功能特性

- ✅ 智能对话（基于 Ollama）
- ✅ 语音合成（ChatTTS）
- ✅ 语音识别（SenseVoice）
- ✅ VRM 3D 角色展示
- ✅ 口型同步
- ✅ 情感表达

更多信息请查看 README.md
'@, [System.Text.Encoding]::UTF8)"

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
echo 📝 启动方式：
echo    • GUI 启动器: 双击 启动GUI.bat（推荐）
echo    • 命令行启动: 双击 启动.bat
echo.
echo 💡 提示：
echo    1. 可以将 %PACKAGE_DIR% 目录复制到任何位置使用
echo    2. GUI 启动器支持一键启动和一键停止
echo    3. 首次运行会自动安装依赖
echo.
pause

