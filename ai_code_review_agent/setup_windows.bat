@echo off
REM Sets up a virtual environment and installs dependencies on Windows.
REM Run this once from the project folder: setup_windows.bat

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on PATH. Install Python 3.11+ from python.org
    echo and check "Add python.exe to PATH" during install, then re-run this script.
    pause
    exit /b 1
)

echo Creating virtual environment in .venv ...
python -m venv .venv

echo Activating virtual environment ...
call .venv\Scripts\activate.bat

echo Upgrading pip ...
python -m pip install --upgrade pip

echo Installing dependencies (this can take a few minutes on first run) ...
pip install -r requirements.txt

if not exist ".env" (
    echo Creating .env from .env.example -- edit it and add your API key.
    copy .env.example .env
)

echo.
echo Setup complete. Next steps:
echo   1. Edit .env and set your LLM_PROVIDER + API key
echo   2. Run:  run_windows.bat
pause
