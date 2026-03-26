@echo off
REM --- Check if git repository is up to date ---
echo Checking for updates in the repository...
git fetch

REM Get hash of current commit and remote branch
for /f "tokens=*" %%i in ('git rev-parse HEAD') do set LOCAL=%%i
for /f "tokens=*" %%i in ('git rev-parse @{u}') do set REMOTE=%%i

if "%LOCAL%"=="%REMOTE%" (
    echo Repository is up to date.
    goto :end
) else (
    echo New version of repository found.
    choice /m "Do you want to download updates from Git? (Y/N)"
    if errorlevel 2 (
        echo Update was not performed.
        goto :end
    ) else (
        echo Performing update...
        git pull
    )
)

REM --- Virtual environment activation and migration ---
echo Activating virtual environment...
if exist venvTBM\Scripts\activate (
    call venvTBM\Scripts\activate
) else if exist venv\Scripts\activate (
    call venv\Scripts\activate
)

echo Updating dependencies...
python -m pip install -r requirements.txt

echo Running makemigrations...
python manage.py makemigrations

echo Running migrate...
python manage.py migrate

echo Compiling translations...
python manage.py compilemessages

echo Checking SSL certificate...
if not exist "cert.pem" (
    echo [INFO] cert.pem not found. It will be generated on first run of start_server.bat using ad-hoc.
)

echo.
echo POZNAMKA: Pokud jde o prvni spusteni po aktualizaci na verzi s vice akcemi,
echo           byla automaticky vytvorena vychozi akce "Vychozi akce".
echo           Prejmenujte ji v aplikaci dle potreby.
echo.
echo Done.
:end
pause
