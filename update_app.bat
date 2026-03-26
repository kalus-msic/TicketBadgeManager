@echo off
REM --- Check if git repository is up to date ---
echo Checking for updates in the repository...
git fetch --all --quiet

REM Get current branch name
for /f "tokens=*" %%i in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%i
echo You are currently on branch: %BRANCH%

REM Get hash of current commit and its upstream
for /f "tokens=*" %%i in ('git rev-parse HEAD') do set LOCAL=%%i
for /f "tokens=*" %%i in ('git rev-parse @{u}') do set REMOTE=%%i

if "%LOCAL%"=="%REMOTE%" (
    echo Branch %BRANCH% is up to date.
    
    if "%BRANCH%"=="main" (
        echo.
        echo Checking if a newer development version (beta) is available...
        for /f "tokens=*" %%i in ('git rev-parse origin/dev') do set DEV_REMOTE=%%i
        if not "%LOCAL%"=="%%DEV_REMOTE%" (
            echo [INFO] A newer version was found in the 'dev' branch.
            choice /m "Do you want to switch to the 'dev' branch and update to the latest beta? (Y/N)"
            if errorlevel 2 (
                echo Staying on main.
                goto :end
            ) else (
                echo Switching to dev...
                git checkout dev
                git pull origin dev
                goto :migrations
            )
        )
    )
    goto :end
) else (
    echo New updates found for branch %BRANCH%.
    choice /m "Do you want to download updates? (Y/N)"
    if errorlevel 2 (
        echo Update was not performed.
        goto :end
    ) else (
        echo Performing update...
        git pull
    )
)

:migrations
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
