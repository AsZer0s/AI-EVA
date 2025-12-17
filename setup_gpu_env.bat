@echo off
chcp 65001 >nul
title AI-EVA GPU 依赖安装工具

echo.
echo ========================================
echo    AI-EVA GPU 依赖安装工具
echo ========================================
echo.
echo 此工具将为便携式 Python 环境安装 GPU 加速依赖
echo 需要 NVIDIA GPU 和 CUDA 支持
echo.

:: 检测 Python 环境
set PYTHON_EXE=
set PIP_EXE=
if exist "python-portable\python.exe" (
    set PYTHON_EXE=python-portable\python.exe
    :: 优先使用 Scripts\pip.exe，更可靠
    if exist "python-portable\Scripts\pip.exe" (
        set PIP_EXE=python-portable\Scripts\pip.exe
    ) else (
        set PIP_EXE=%PYTHON_EXE% -m pip
    )
    echo ✅ 检测到便携式 Python 环境
) else (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo ❌ 错误：未找到 Python 环境
        echo.
        echo 💡 解决方案：
        echo    1. 先运行 setup_python_env.bat 配置便携式 Python 环境
        echo    2. 或确保系统已安装 Python 3.8+ 并添加到 PATH
        echo.
        pause
        exit /b 1
    )
    set PYTHON_EXE=python
    :: 尝试使用 pip.exe，否则使用 python -m pip
    pip --version >nul 2>&1
    if errorlevel 1 (
        set PIP_EXE=%PYTHON_EXE% -m pip
    ) else (
        set PIP_EXE=pip
    )
    echo ✅ 使用系统 Python 环境
)

echo.
echo 使用的 Python: %PYTHON_EXE%
%PYTHON_EXE% --version
echo 使用的 pip: %PIP_EXE%
%PIP_EXE% --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  警告：pip 不可用，尝试修复...
    :: 修复 python310._pth 或 python311._pth
    if exist "python-portable\python310._pth" (
        echo 修复 python310._pth...
        (echo python310.zip
        echo .
        echo # Uncomment to run site.main^(^) automatically
        echo import site) > python-portable\python310._pth
    )
    if exist "python-portable\python311._pth" (
        echo 修复 python311._pth...
        (echo python311.zip
        echo .
        echo # Uncomment to run site.main^(^) automatically
        echo import site) > python-portable\python311._pth
    )
    :: 重新检测 pip
    if exist "python-portable\Scripts\pip.exe" (
        set PIP_EXE=python-portable\Scripts\pip.exe
    ) else (
        set PIP_EXE=%PYTHON_EXE% -m pip
    )
    echo ✅ pip 修复完成
)
echo.

:: 检查 requirements-gpu.txt 是否存在
if not exist "requirements-gpu.txt" (
    echo ❌ 错误：未找到 requirements-gpu.txt
    echo 请确保在项目根目录运行此脚本
    pause
    exit /b 1
)

:: 检查 CUDA 版本（可选）
echo 🔍 检测 CUDA 版本...
nvcc --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  警告：未检测到 CUDA，将使用 CUDA 11.8 版本
    echo 💡 提示：即使未检测到 CUDA，也可以安装 GPU 版本的 PyTorch
    echo    如果后续有 GPU，可以直接使用
    set CUDA_VERSION=cu118
) else (
    echo ✅ 检测到 CUDA
    nvcc --version | findstr "release"
    echo.
    echo 请选择 PyTorch CUDA 版本：
    echo   1. CUDA 11.8 (推荐，兼容性最好)
    echo   2. CUDA 12.1 (需要 CUDA 12.1+)
    echo   3. CUDA 12.4 (需要 CUDA 12.4+)
    set /p cuda_choice="请输入选项 (1-3，默认 1): "
    if "%cuda_choice%"=="" set cuda_choice=1
    if "%cuda_choice%"=="1" set CUDA_VERSION=cu118
    if "%cuda_choice%"=="2" set CUDA_VERSION=cu121
    if "%cuda_choice%"=="3" set CUDA_VERSION=cu124
)

echo.
echo ========================================
echo    步骤 1: 卸载现有 PyTorch
echo ========================================
echo.
set /p confirm="是否卸载现有的 PyTorch？(Y/N，默认 Y): "
if /i "%confirm%"=="" set confirm=Y
if /i "%confirm%"=="Y" (
    echo 正在卸载 PyTorch...
    %PIP_EXE% uninstall torch torchvision torchaudio -y
    echo ✅ PyTorch 卸载完成
) else (
    echo ⏭️  跳过卸载步骤
)

echo.
echo ========================================
echo    步骤 2: 安装 PyTorch GPU 版本
echo ========================================
echo.
echo 请选择下载源：
echo   1. PyTorch 官方源（推荐，但可能较慢）
echo   2. 清华大学镜像（国内用户推荐）
set /p mirror_choice="请输入选项 (1-2，默认 1): "
if "%mirror_choice%"=="" set mirror_choice=1

echo.
echo 正在安装 PyTorch GPU 版本 (CUDA %CUDA_VERSION%)...
echo 这可能需要几分钟，请耐心等待...
echo.

if "%mirror_choice%"=="2" (
    echo 使用清华大学镜像源...
    %PIP_EXE% install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/%CUDA_VERSION% -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade
) else (
    %PIP_EXE% install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/%CUDA_VERSION% --upgrade
)

if errorlevel 1 (
    echo.
    echo ❌ PyTorch 安装失败
    echo 💡 提示：
    echo    1. 检查网络连接
    echo    2. 可以尝试使用国内镜像：
    echo       pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/%CUDA_VERSION% -i https://pypi.tuna.tsinghua.edu.cn/simple
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ PyTorch GPU 版本安装完成

echo.
echo ========================================
echo    步骤 3: 验证 CUDA 是否可用
echo ========================================
echo.
echo 正在验证 CUDA...
%PYTHON_EXE% -c "import torch; print('✅ CUDA 可用:', torch.cuda.is_available()); print('CUDA 版本:', torch.version.cuda if torch.cuda.is_available() else 'N/A'); print('GPU 设备数量:', torch.cuda.device_count() if torch.cuda.is_available() else 0)"

if errorlevel 1 (
    echo ⚠️  CUDA 验证失败，但安装将继续
) else (
    echo ✅ CUDA 验证完成
)

echo.
echo ========================================
echo    步骤 4: 安装其他 GPU 依赖
echo ========================================
echo.
echo 请选择下载源：
echo   1. PyPI 官方源（推荐，但可能较慢）
echo   2. 清华大学镜像（国内用户推荐）
set /p mirror_choice2="请输入选项 (1-2，默认 1): "
if "%mirror_choice2%"=="" set mirror_choice2=1

echo.
echo 正在安装 requirements-gpu.txt 中的其他依赖...
echo 这可能需要较长时间，请耐心等待...
echo.

if "%mirror_choice2%"=="2" (
    echo 使用清华大学镜像源...
    %PIP_EXE% install -r requirements-gpu.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade
) else (
    %PIP_EXE% install -r requirements-gpu.txt --upgrade
)

if errorlevel 1 (
    echo.
    echo ❌ 依赖安装失败
    echo 💡 提示：可以尝试使用国内镜像加速：
    echo    pip install -r requirements-gpu.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo    GPU 依赖安装完成！
echo ========================================
echo.
echo 📋 安装摘要：
echo   - Python: %PYTHON_EXE%
echo   - PyTorch CUDA 版本: %CUDA_VERSION%
echo   - 依赖文件: requirements-gpu.txt
echo.
echo ✅ 下一步：
echo    1. 运行 AAA一键启动.bat 或 start-all.bat 启动服务
echo    2. 确保在 .env 文件中设置 USE_GPU=true（如果使用）
echo.
pause

