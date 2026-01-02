@echo off
SETLOCAL

:: Title of the window
TITLE Sales Analysis App

:: Check for Portable Python first
IF EXIST "python_portable\python-3.13.11-embed-amd64\python.exe" (
    echo [INFO] Using Portable Python...
    .\python_portable\python-3.13.11-embed-amd64\python.exe -m streamlit run app.py
    pause
    exit /b
)

:: Check if Python is installed (Fallback)
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in your PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    echo Press any key to exit...
    pause >nul
    exit /b
)

:: Check if venv exists
IF NOT EXIST "venv" (
    echo First time setup: Creating virtual environment...
    python -m venv venv
    
    echo Installing dependencies...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    
    echo Setup complete!
) ELSE (
    echo Environment found. Activating...
    call venv\Scripts\activate.bat
)

echo.
echo Starting the application...
echo Your browser should open automatically.
echo.

:: Run the app
streamlit run app.py

pause

