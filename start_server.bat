@echo off
REM Virtual environment activation
call venvTBM\Scripts\activate

REM Start server in a new command window (non-blocking execution)
REM Use ad-hoc if files don't exist, otherwise use the persistent files
if exist cert.pem (
    start cmd /k "python manage.py runserver_plus 0.0.0.0:8000 --cert-file cert.pem --key-file key.pem"
) else (
    start cmd /k "python manage.py runserver_plus 0.0.0.0:8000 --cert-file ad-hoc"
)

REM Wait 5 seconds
timeout /t 5 /nobreak > nul

REM Open default browser with the given URL
start https://127.0.0.1:8000