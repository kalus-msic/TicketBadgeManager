@echo off
setlocal enabledelayedexpansion

REM --- Check if Python is installed ---
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8 or higher and add it to PATH.
    pause
    exit /b
)

REM --- Generate SECRET_KEY using simple batch method ---
echo Generating SECRET_KEY...
set "CHARS=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
set "SECRET_KEY="

REM Initialize random seed
set /a "seed=%random%"

REM Generate 50 character key
for /L %%i in (1,1,50) do (
    set /a "rand=!random! %% 62"
    for %%j in (!rand!) do set "char=!CHARS:~%%j,1!"
    set "SECRET_KEY=!SECRET_KEY!!char!"
)

REM --- Final check if SECRET_KEY was generated ---
if "%SECRET_KEY%"=="" (
    echo [ERROR] Failed to generate SECRET_KEY.
    pause
    exit /b
)

echo Random SECRET_KEY generated successfully.

REM --- Check if we're in the root project directory ---
if not exist "manage.py" (
    echo [ERROR] manage.py file not found. Run this script from the root project directory.
    pause
    exit /b
)

REM --- Create a virtual environment if it doesn't exist ---
if not exist "venvTBM\Scripts\activate" (
    echo Virtual environment not found. Creating virtual environment...
    python -m venv venvTBM
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
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    pause
    exit /b
)

REM --- Automatically create the .env file with random SECRET_KEY ---
echo [INFO] Creating .env file with a random SECRET_KEY...

REM --- Create .env file ---
(
echo # ========================
echo # Django settings
echo # ========================
echo SECRET_KEY=%SECRET_KEY%
echo DEBUG=False
echo ALLOWED_HOSTS=127.0.0.1,localhost,*
echo # ========================
echo # Database
echo # ========================
echo DATABASE_URL=sqlite:///db.sqlite3
echo # ========================
echo # Eventee API
echo # ========================
echo EVENTEE_API_TOKEN=
echo # ========================
echo # Logging
echo # ========================
echo LOG_LEVEL=INFO
echo # ========================
echo # Security settings
echo # ========================
echo SECURE_SSL_REDIRECT=False
echo SESSION_COOKIE_SECURE=False
echo CSRF_COOKIE_SECURE=False
echo # ========================
echo # Authentication
echo # ========================
echo DISABLE_AUTH=True
echo # ========================
echo # Rate limiting
echo # ========================
echo RATELIMIT_ENABLE=True
echo RATELIMIT_USE_CACHE=default
) > .env

echo [INFO] .env file created successfully with random SECRET_KEY.

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

echo Compiling translations...
python manage.py compilemessages
if errorlevel 1 (
    echo [WARNING] Error compiling translations. Ensure gettext is installed.
)


REM --- Collect static files ---
echo Collecting static files...
python manage.py collectstatic --noinput
if errorlevel 1 (
    echo [WARNING] Error collecting static files. This may not be critical.
)

REM --- Generate SSL certificate ---
if not exist "cert.pem" (
    echo Generating SSL certificate...
    REM runserver_plus can generate ad-hoc, but we generate it once to avoid browser warnings changing every time
    REM We use a dummy command to trigger werkzeug certificate generation if possible, 
    REM or just let the user know it will be generated on first run.
    echo [INFO] SSL certificate will be generated on first run by runserver_plus.
)

REM --- Final Message ---
echo.
echo ========================================
echo Installation completed successfully!
echo ========================================
echo.
echo The .env file has been created. It is recommended to check and update the following:
echo - EVENTEE_API_TOKEN (add your Eventee API token)
echo - ALLOWED_HOSTS (set appropriate allowed hosts for production)
echo - DISABLE_AUTH (set to False to enable authentication in production)
echo.
echo Default user credentials:
echo   Username: TBM
echo   Password: TBM
echo   Note: This is a staff user created during migration
echo.
echo To start the development server:
echo   start_server.bat
echo.
echo Or manually:
echo   call venvTBM\Scripts\activate
echo   python manage.py runserver_plus 0.0.0.0:8000 --cert-file cert.pem --key-file key.pem
echo.
echo For more information, please refer to the README file.
pause
