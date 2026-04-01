@echo off
REM Artha Vyavastha — one-time setup and launch (Windows)

cd /d "%~dp0"

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Installing dependencies...
pip install -q -r requirements.txt

echo.
echo Starting Artha Vyavastha...
echo The app will open in your browser shortly.
echo.
streamlit run app.py
