@echo off
TITLE C2 Scraper Suite - Dependency Installer
echo [!] Checking Python installation...
python --version
if errorlevel 1 (
    echo [ERROR] Python is not installed or added to PATH!
    pause
    exit /b
)

echo.
echo [!] Upgrading pip package manager...
python -m pip install --upgrade pip

echo.
echo [!] Installing required packages from requirements.txt...
if exist requirements.txt (
    python -m pip install -r requirements.txt
) else (
    echo [!] requirements.txt not found. Installing default packages manually...
    python -m pip install tkinterweb
)

echo.
echo [SUCCESS] All dependencies installed successfully!
echo You can now run gui_commander.py
pause