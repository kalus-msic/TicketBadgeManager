@echo off
REM --- Zkontrolujeme aktuálnost git repozitáře ---
echo Kontroluji aktualizace v repozitari...
git fetch

REM Zjistíme hash aktuálního commitu a vzdálené větve
for /f "tokens=*" %%i in ('git rev-parse HEAD') do set LOCAL=%%i
for /f "tokens=*" %%i in ('git rev-parse @{u}') do set REMOTE=%%i

if "%LOCAL%"=="%REMOTE%" (
    echo Repozitar je aktualni.
) else (
    echo Nalezena nová verze repozitare.
    choice /m "Chcete stáhnout aktualizace z Gitu? (Y/N)"
    if errorlevel 2 (
        echo Aktualizace nebyla provedena.
        goto :end
    ) else (
        echo Provadim aktualizaci...
        git pull
    )
)

REM --- Aktivace virtuálního prostředí a migrace ---
echo Aktivace virtualniho prostredi...
call venvTBM\Scripts\activate

echo Spoustim makemigrations...
python manage.py makemigrations

echo Spoustim migrate...
python manage.py migrate

echo Hotovo.
:end
pause
