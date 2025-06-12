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
call venvTBM\Scripts\activate

echo Running makemigrations...
python manage.py makemigrations

echo Running migrate...
python manage.py migrate

echo Done.
:end
pause
