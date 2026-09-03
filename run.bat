@echo off
title HyperOS-GlobalConvert - Launcher
echo ===============================================================
echo    HyperOS GlobalConvert - System Apps APK Patcher
echo    Repository: https://github.com/mertcqnkld/HyperOS-GlobalConvert
echo ===============================================================
echo.
echo [1] Start Modern Web UI (Browser based)
echo [2] Start CLI Interface (Console based)
echo [3] Push to GitHub
echo.
set /p choice="Select an option (1-3, Default: 1): "

if "%choice%"=="2" (
    python main.py
) else if "%choice%"=="3" (
    python scripts/github_push.py
) else (
    echo Starting Web UI on http://localhost:8080 ...
    start http://localhost:8080
    python web/app.py 8080
)
pause
