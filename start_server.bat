@echo off
REM Aktivace virtuálního prostředí
call venvTBM\Scripts\activate

REM Spuštění serveru v novém příkazovém okně (neblokující spuštění)
start cmd /k "python manage.py runsslserver 0.0.0.0:8000"

REM Počká 5 sekund
timeout /t 5 /nobreak > nul

REM Otevře výchozí prohlížeč s danou URL
start https://127.0.0.1:8000