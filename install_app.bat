@echo off
setlocal

REM --- Required Python version ---
set "REQUIRED_PYTHON=3.11.9"
set "PYTHON_EXE=python"

REM --- Check if we're in the root project directory ---
if not exist "manage.py" (
    echo [ERROR] manage.py file not found. Run this script from the root project directory.
    pause
    exit /b
)

REM --- Check if python is available ---
where %PYTHON_EXE% >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH. Make sure it's installed and added to PATH.
    pause
    exit /b
)

REM --- Check the exact version of Python ---
for /f "delims=" %%v in ('%PYTHON_EXE% --version 2^>^&1') do set "VERSION_OUTPUT=%%v"
echo Detected version: %VERSION_OUTPUT%

echo %VERSION_OUTPUT% | findstr /C:"Python %REQUIRED_PYTHON%" >nul
if errorlevel 1 (
    echo [ERROR] Python version is not %REQUIRED_PYTHON%. Install the correct version.
    pause
    exit /b
)

REM --- Create a virtual environment if it doesn't exist ---
if not exist "venvTBM\Scripts\activate" (
    echo Virtual environment not found. Creating virtual environment using %PYTHON_EXE%...
    %PYTHON_EXE% -m venv venvTBM
    if errorlevel 1 (
        echo [ERROR] Error creating virtual environment.
        pause
        exit /b
    )
) else (
    echo Virtual environment venvTBM found.
)

REM --- Activate the virtual environment ---
call venvTBM\Scripts\activate

REM --- Install required packages ---
echo Installing packages from requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Error installing packages. Check requirements.txt.
    pause
    exit /b
)

REM --- Run database migrations ---
echo Running makemigrations...
python manage.py makemigrations
if errorlevel 1 (
    echo [ERROR] Error creating migrations.
    pause
    exit /b
)

echo Running migrate...
python manage.py migrate
if errorlevel 1 (
    echo [ERROR] Error performing migrations.
    pause
    exit /b
)

echo Installation was successful.
echo Don't forget to update SECRET_KEY and ALLOWED_HOSTS in the settings.py file according to the README.md.
pause