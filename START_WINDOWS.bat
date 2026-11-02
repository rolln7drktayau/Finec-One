@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (echo Python 3.11+ is required & pause & exit /b 1)
if not exist .venv (python -m venv .venv)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
echo Opening http://127.0.0.1:8000 after the server starts...
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://127.0.0.1:8000"
python run.py
pause
