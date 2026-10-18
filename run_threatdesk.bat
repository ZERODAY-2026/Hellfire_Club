@echo off
setlocal
cd /d "%~dp0"

echo ==========================================================
echo       Launching ThreatDesk Enterprise Intelligence UI
echo       (Squarespace-inspired Editorial Theme)
echo ==========================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Python virtual environment not found at .venv!
    echo Please ensure the virtual environment is set up.
    pause
    exit /b 1
)

set PYTHONPATH=%CD%
echo Starting Streamlit server...
.venv\Scripts\python -m streamlit run app/ui.py

endlocal
pause
