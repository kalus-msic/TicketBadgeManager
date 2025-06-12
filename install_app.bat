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

REM --- Generate SECRET_KEY using PowerShell ---
echo Generating SECRET_KEY...
for /f "delims=" %%i in ('powershell -Command "[System.Web.Security.Membership]::GeneratePassword(50, 10) -replace '\"', ''"') do set "SECRET_KEY=%%i"

REM --- If PowerShell method fails, use alternative method ---
if "%SECRET_KEY%"=="" (
    echo PowerShell method failed, using alternative method...
    REM Generate using current timestamp and random numbers
    for /f "tokens=1-3 delims=:." %%a in ('echo %time%') do (
        set /a "seed=%%a%%b%%c"
    )
    set "CHARS=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    set "SECRET_KEY="
    for /L %%i in (1,1,50) do (
        set /a "rand=!random! %% 62"
        for /f %%c in ('cmd /c "echo !CHARS:~%%rand,1!"') do (
            set "SECRET_KEY=!SECRET_KEY!%%c"
        )
    )
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

REM --- Create default superuser if it doesn't exist ---
echo Checking for default superuser...
python -c "import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TicketBadgeManager.settings'); import django; django.setup(); from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='TBM').exists() or User.objects.create_superuser('TBM', 'tbm@example.com', 'TBM')" 2>nul
if errorlevel 1 (
    echo [WARNING] Could not create default user. You may need to create it manually using: python manage.py createsuperuser
) else (
    echo Default superuser 'TBM' created or already exists.
)

REM --- Collect static files ---
echo Collecting static files...
python manage.py collectstatic --noinput
if errorlevel 1 (
    echo [WARNING] Error collecting static files. This may not be critical.
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
echo Default superuser credentials (if created):
echo   Username: TBM
echo   Password: TBM
echo.
echo To start the development server:
echo   call venvTBM\Scripts\activate
echo   python manage.py runserver
echo.
echo For more information, please refer to the README file.
pause
