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

REM --- Ask user if they want to create a new .env file with random SECRET_KEY ---
set /p CREATE_ENV="Do you want to automatically generate a basic .env file with a random SECRET_KEY? (y/n): "
if /i "%CREATE_ENV%"=="y" (
    REM --- Generate .env file with random SECRET_KEY ---
    echo [INFO] Creating .env file with a random SECRET_KEY...

    REM --- Generate a random SECRET_KEY ---
    for /f "delims=" %%x in ('python -c "import secrets; print(secrets.token_urlsafe(50))"') do set "SECRET_KEY=%%x"

    REM --- Create .env file ---
    (echo # ======================== && 
    echo # Django settings && 
    echo # ======================== && 
    echo SECRET_KEY=%SECRET_KEY% && 
    echo DEBUG=False && 
    echo ALLOWED_HOSTS=127.0.0.1,localhost,* && 
    echo # ======================== && 
    echo # Database && 
    echo # ======================== && 
    echo DATABASE_URL=sqlite:///db.sqlite3 && 
    echo # ======================== && 
    echo # Eventee API && 
    echo # ======================== && 
    echo EVENTEE_API_TOKEN= && 
    echo # ======================== && 
    echo # Logging && 
    echo # ======================== && 
    echo LOG_LEVEL=INFO && 
    echo # ======================== && 
    echo # Security settings && 
    echo # ======================== && 
    echo SECURE_SSL_REDIRECT=False && 
    echo SESSION_COOKIE_SECURE=False && 
    echo CSRF_COOKIE_SECURE=False && 
    echo # ======================== && 
    echo # Authentication && 
    echo # ======================== && 
    echo DISABLE_AUTH=True && 
    echo # ======================== && 
    echo # Rate limiting && 
    echo # ======================== && 
    echo RATELIMIT_ENABLE=True && 
    echo RATELIMIT_USE_CACHE=default) > .env

    echo [INFO] .env file created successfully with random SECRET_KEY.
) else (
    echo [INFO] .env file was not created. Please create the .env file manually and update SECRET_KEY and ALLOWED_HOSTS.
)

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
echo It is recommended to check and update the following in your .env file:
echo - SECRET_KEY (make sure it is securely set)
echo - ALLOWED_HOSTS (set appropriate allowed hosts)
echo - DISABLE_AUTH (set to False to enable authentication, if needed)
echo
echo Default user "TBM" has been created (username: TBM, password: TBM).
echo For more information, please refer to the "Installation" section of the README file.
pause
