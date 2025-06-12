@echo off
setlocal enabledelayedexpansion

REM --- Define characters to use in the SECRET_KEY (including special characters) ---
set "CHARS=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+[{]}\\|;:'\",<.>/?`~"

REM --- Initialize SECRET_KEY as empty ---
set "SECRET_KEY="

REM --- Generate a random SECRET_KEY with alphanumeric characters (letters, digits, and special characters) ---
for /L %%i in (1,1,50) do (
    set /a "RANDOM_INDEX=!random! %% 94"  REM Random number between 0 and 93 (for 94 characters)
    set "CHAR="
    for %%c in (%CHARS%) do (
        set /a "COUNTER+=1"
        if "!COUNTER!"=="!RANDOM_INDEX!" (
            set "CHAR=%%c"
        )
    )
    set "SECRET_KEY=!SECRET_KEY!!CHAR!"
    set COUNTER=0
)

REM --- Check if SECRET_KEY was generated ---
if "%SECRET_KEY%"=="" (
    echo [ERROR] Failed to generate SECRET_KEY.
    pause
    exit /b
)

echo Random SECRET_KEY generated: %SECRET_KEY%

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

REM --- Automatically create the .env file with random SECRET_KEY ---
echo [INFO] Creating .env file with a random SECRET_KEY...

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

REM --- Final Message ---
echo Installation was successful.
echo The .env file has been created. It is recommended to check and update the following in your .env file:
echo - SECRET_KEY (make sure it is securely set)
echo - ALLOWED_HOSTS (set appropriate allowed hosts)
echo - DISABLE_AUTH (set to False to enable authentication, if needed)
echo
echo Default user "TBM" has been created (username: TBM, password: TBM).
echo For more information, please refer to the "Installation" section of the README file.
pause
