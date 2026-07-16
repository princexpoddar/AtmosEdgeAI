@echo off
cd /d "%~dp0"
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 --reload
pause
