@echo off
cd /d "%~dp0"
REM Set up a local virtual environment with the `py` launcher, then run the app.
if not exist venv\Scripts\python.exe (
    echo Creating virtual environment (py -m venv venv)
    py -m venv venv
    venv\Scripts\python.exe -m pip install --upgrade pip
    venv\Scripts\python.exe -m pip install -r requirements.txt
)
venv\Scripts\python.exe main.py
