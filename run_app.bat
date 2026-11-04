@echo off
title EduPredict AI Server
echo ============================================================
echo           EduPredict AI - Capstone Web Server
echo ============================================================
echo.
echo Initializing local FastAPI backend on http://127.0.0.1:8000/
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

:: Automatically open the web browser to the application
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8000/"

:: Start FastAPI server
"%PYTHON_EXE%" -m uvicorn src.api:app --host 127.0.0.1 --port 8000 --reload
pause
