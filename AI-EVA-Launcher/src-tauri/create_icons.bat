@echo off
chcp 65001 >nul
echo ========================================
echo 创建占位符图标文件
echo ========================================
echo.

if not exist icons mkdir icons

echo 检查 Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Python
    echo.
    echo 请手动创建图标文件，或安装 Python 后运行此脚本
    echo.
    echo 图标文件位置: icons/
    echo 需要的文件:
    echo   - 32x32.png
    echo   - 128x128.png
    echo   - 128x128@2x.png (256x256)
    echo   - icon.ico
    echo   - icon.icns (macOS, 可选)
    echo.
    echo 可以使用在线工具生成:
    echo   https://www.icoconverter.com/
    echo.
    pause
    exit /b 1
)

echo ✅ Python 已安装
python --version

echo.
echo 检查 Pillow...
python -c "import PIL" 2>nul
if %errorlevel% neq 0 (
    echo ⚠️  Pillow 未安装，正在安装...
    pip install Pillow
    if %errorlevel% neq 0 (
        echo ❌ Pillow 安装失败
        pause
        exit /b 1
    )
)

echo ✅ Pillow 已安装

echo.
echo 创建占位符图标...
python create_placeholder_icons.py

echo.
echo ========================================
echo 图标创建完成！
echo ========================================
echo.
pause

