@echo off
REM ============================================================
REM  BESCOM Fault-to-Recovery - Windows one-click starter
REM  Double-click this file to run the dashboard locally.
REM ============================================================
setlocal

cd /d "%~dp0"

echo.
echo  [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo  ERROR: Python is not installed or not on PATH.
  echo  Install Python 3.10+ from https://www.python.org/downloads/windows/
  echo  IMPORTANT: tick "Add Python to PATH" during install.
  echo.
  pause
  exit /b 1
)

echo.
echo  [2/4] Setting up virtual environment ^(first run only^)...
if not exist venv (
  python -m venv venv
)
call venv\Scripts\activate.bat

echo.
echo  [3/4] Installing dependencies ^(first run only^)...
pip install -q -r requirements.txt

echo.
echo  [4/4] Starting BESCOM dashboard...
echo  --------------------------------------------------------
echo   Open in browser:  http://localhost:5000
echo   Login:            admin@bescom.sim  /  demo123
echo   ^(any email + 3+ char password works^)
echo  --------------------------------------------------------
echo   Press Ctrl+C in this window to stop the server.
echo.

python app.py

pause
