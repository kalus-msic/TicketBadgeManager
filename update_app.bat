@echo off
REM --- Zkontrolujeme aktuálnost git repozitáře ---
echo Kontroluji aktualizace v repozitáři...
git fetch

REM Zjistíme hash aktuálního commitu a vzdálené větve
for /f "tokens=*" %%i in ('git rev-parse HEAD') do set LOCAL=%%i
for /f "tokens=*" %%i in ('git rev-parse @{u}') do set REMOTE=%%i

if "%LOCAL%"=="%REMOTE%" (
    echo Repozitář je aktualizován.
) else (
    echo Nalezena nová verze repozitáře.
    choice /m "Chcete stáhnout aktualizace z Gitu? (Y/N)"
    if errorlevel 2 (
        echo Aktualizace nebyla provedena.
        goto :end
    ) else (
        echo Provádím aktualizaci...
        git pull
    )
)

REM --- Aktivace virtuálního prostředí a migrace ---
echo Aktivace virtuálního prostředí...
call venvTBM\Scripts\activate

echo Spoustim makemigrations...
python manage.py makemigrations

echo Spoustim migrate...
python manage.py migrate

echo Hotovo.
:end
pause
