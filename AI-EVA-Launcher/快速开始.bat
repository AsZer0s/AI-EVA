@echo off
chcp 65001 >nul
echo ========================================
echo AI-EVA Launcher 快速开始
echo ========================================
echo.

echo 检查 Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Node.js，请先安装 Node.js 18+
    echo 下载地址: https://nodejs.org/
    pause
    exit /b 1
)

echo ✅ Node.js 已安装
node --version

echo.
echo 检查 Rust...
where rustc >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Rust，请先安装 Rust
    echo 安装地址: https://www.rust-lang.org/tools/install
    pause
    exit /b 1
)

echo ✅ Rust 已安装
rustc --version

echo.
echo 检查 Git...
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  未找到 Git，IndexTTS2 克隆功能将不可用
    echo 下载地址: https://git-scm.com/downloads
) else (
    echo ✅ Git 已安装
    git --version
)

echo.
echo ========================================
echo 开始安装依赖...
echo ========================================
echo.

echo 安装 Node.js 依赖...
call npm install
if %errorlevel% neq 0 (
    echo ❌ npm install 失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo 依赖安装完成！
echo ========================================
echo.
echo 下一步:
echo 1. 运行 "npm run tauri dev" 启动开发模式
echo 2. 运行 "npm run tauri build" 构建生产版本
echo.
pause

