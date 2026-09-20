@echo off
title Mini-Apollo Lead Engine
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found! Please ensure .venv exists.
    pause
    exit /b 1
)

echo Starting Mini-Apollo Lead Engine...
.venv\Scripts\python.exe lead_engine.py
pause
