@echo off
chcp 65001 >nul
title AI-EVA Python 环境配置工具

echo.
echo ========================================
echo    AI-EVA Python 环境配置工具
echo ========================================
echo.
echo 此工具将下载并配置便携式 Python 环境
echo 配置完成后无需系统安装 Python 即可运行
echo.

set PYTHON_DIR=python-portable
set PYTHON_VERSION=3.10.9
set PYTHON_EMBED_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/python-%PYTHON_VERSION%-embed-amd64.zip

:: 检查是否已存在 Python 环境
if exist "%PYTHON_DIR%\python.exe" (
    echo 检测到已存在的 Python 环境
    echo.
    set /p confirm="是否重新下载配置？(Y/N): "
    if /i not "%confirm%"=="Y" (
        echo 已取消操作
        pause
        exit /b 0
    )
    echo 清理旧环境...
    rmdir /s /q "%PYTHON_DIR%"
)

:: 创建目录
echo.
echo 创建 Python 环境目录...
mkdir "%PYTHON_DIR%" 2>nul
cd "%PYTHON_DIR%"

:: 下载 Python Embedded
echo.
echo 正在下载 Python %PYTHON_VERSION% Embedded...
echo 下载地址: %PYTHON_EMBED_URL%
echo.

:: 检查是否有 curl 或 PowerShell
where curl >nul 2>&1
if %errorlevel% == 0 (
    echo 使用 curl 下载...
    curl -L -o python-embed.zip "%PYTHON_EMBED_URL%"
) else (
    echo 使用 PowerShell 下载...
    powershell -Command "Invoke-WebRequest -Uri '%PYTHON_EMBED_URL%' -OutFile 'python-embed.zip'"
)

if not exist "python-embed.zip" (
    echo  下载失败请检查网络连接
    echo 提示可以手动下载以下文件并解压到 %PYTHON_DIR% 目录
    echo    %PYTHON_EMBED_URL%
    pause
    exit /b 1
)

echo 下载完成

:: 解压
echo.
echo 正在解压...
powershell -Command "Expand-Archive -Path 'python-embed.zip' -DestinationPath '.' -Force"
del python-embed.zip

if not exist "python.exe" (
    echo  解压失败
    pause
    exit /b 1
)

echo 解压完成

:: 配置 Python
echo.
echo 配置 Python 环境...

:: 创建 python310._pth 配置文件
(echo python310.zip
echo .
echo # Uncomment to run site.main^(^) automatically
echo import site) > python310._pth

:: 安装 pip
echo.
echo 安装 pip...
python.exe -m ensurepip --upgrade --default-pip

if errorlevel 1 (
    echo   ensurepip 失败尝试手动安装 pip...
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    python.exe get-pip.py
    del get-pip.py
)

echo  pip 安装完成

:: 验证配置文件
if not exist "python310._pth" (
    echo.
    echo ⚠️  警告：python310._pth 文件创建失败，正在尝试修复...
    (echo python310.zip
    echo .
    echo # Uncomment to run site.main^(^) automatically
    echo import site) > python310._pth
)

if exist "python310._pth" (
    echo ✅ python310._pth 配置文件已创建
    echo.
    echo 验证 Python 环境...
    python.exe --version >nul 2>&1
    if errorlevel 1 (
        echo ⚠️  Python 启动测试失败，配置文件可能有问题
        echo 💡 提示：可以运行 修复python配置.bat 修复配置文件
    ) else (
        echo ✅ Python 环境正常
        python.exe --version
    )
) else (
    echo ❌ python310._pth 配置文件创建失败
    echo 💡 提示：可以手动创建此文件，内容如下：
    echo    python310.zip
    echo    .
    echo    # Uncomment to run site.main^(^) automatically
    echo    import site
)

:: 返回上级目录
cd ..

echo.
echo ========================================
echo     Python 环境配置完成！
echo ========================================
echo.
echo  Python 目录: %PYTHON_DIR%
echo  Python 版本: %PYTHON_VERSION%
echo.
echo  使用方法：
echo    1. 启动脚本会自动检测并使用便携式 Python
echo    2. 或手动使用 %PYTHON_DIR%\python.exe
echo.
echo  下一步：
echo    1. 运行 启动GUI.bat 或 start-all.bat 启动服务
echo    2. 首次运行会自动安装项目依赖
echo.
pause

