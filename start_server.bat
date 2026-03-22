@echo off
REM Virtual environment activation
call venvTBM\Scripts\activate

REM Start server in a new command window (non-blocking execution)
start cmd /k "python manage.py runsslserver 0.0.0.0:8000"

REM Wait 5 seconds
timeout /t 5 /nobreak > nul

REM Open default browser with the given URL
start https://127.0.0.1:8000