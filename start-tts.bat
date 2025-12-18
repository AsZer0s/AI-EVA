@echo off
chcp 65001 >nul
cd /d %~dp0
echo ========================================
echo IndexTTS2 服务启动
echo ========================================
echo.
python -m uvicorn indextts_api:app --host 0.0.0.0 --port 9966 --log-level info --access-log
pause