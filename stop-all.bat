@echo off
chcp 65001 >nul
title AI-EVA 停止所有服务

echo.
echo ========================================
echo    AI-EVA Demo 停止所有服务
echo ========================================
echo.

:: 停止占用端口的进程
echo 🔍 查找并停止服务进程...

:: 停止 ChatTTS (端口 9966)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":9966" ^| findstr "LISTENING"') do (
    echo 停止 ChatTTS 服务 (PID: %%a)...
    taskkill /PID %%a /F >nul 2>&1
)

:: 停止 SenseVoice (端口 50000)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":50000" ^| findstr "LISTENING"') do (
    echo 停止 SenseVoice 服务 (PID: %%a)...
    taskkill /PID %%a /F >nul 2>&1
)

:: 停止前端服务 (端口 8000)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo 停止前端服务 (PID: %%a)...
    taskkill /PID %%a /F >nul 2>&1
)

:: 停止 Ollama (端口 11434)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":11434" ^| findstr "LISTENING"') do (
    echo 停止 Ollama 服务 (PID: %%a)...
    taskkill /PID %%a /F >nul 2>&1
)

:: 停止 Python 相关进程（谨慎使用）
echo.
echo ⚠️  注意：以下命令会停止所有 uvicorn 和 http.server 进程
echo    如果只运行了 AI-EVA，可以安全执行
echo.
set /p confirm="是否停止所有 Python Web 服务进程？(Y/N): "
if /i "%confirm%"=="Y" (
    taskkill /F /IM uvicorn.exe >nul 2>&1
    taskkill /F /FI "WINDOWTITLE eq Frontend*" >nul 2>&1
    taskkill /F /FI "WINDOWTITLE eq ChatTTS*" >nul 2>&1
    taskkill /F /FI "WINDOWTITLE eq SenseVoice*" >nul 2>&1
    echo ✅ 已停止所有 Python Web 服务进程
)

echo.
echo ========================================
echo    ✅ 服务停止完成
echo ========================================
echo.
pause

