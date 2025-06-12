@echo off
setlocal

REM --- Požadovaná verze Pythonu ---
set "REQUIRED_PYTHON=3.11.9"
set "PYTHON_EXE=python"

REM --- Ověření, že se nacházíme v kořenovém adresáři projektu ---
if not exist "manage.py" (
    echo [CHYBA] Soubor manage.py nebyl nalezen. Spusťte tento skript v kořenovém adresáři projektu.
    pause
    exit /b
)

REM --- Kontrola, že python je dostupný ---
where %PYTHON_EXE% >nul 2>&1
if errorlevel 1 (
    echo [CHYBA] Python nebyl nalezen v PATH. Ujistěte se, že je nainstalován a přidán do PATH.
    pause
    exit /b
)

REM --- Ověření přesné verze Pythonu ---
for /f "delims=" %%v in ('%PYTHON_EXE% --version 2^>^&1') do set "VERSION_OUTPUT=%%v"
echo Detekována verze: %VERSION_OUTPUT%

echo %VERSION_OUTPUT% | findstr /C:"Python %REQUIRED_PYTHON%" >nul
if errorlevel 1 (
    echo [CHYBA] Verze Pythonu není %REQUIRED_PYTHON%. Nainstalujte správnou verzi.
    pause
    exit /b
)

REM --- Vytvoření virtuálního prostředí, pokud ještě neexistuje ---
if not exist "venvTBM\Scripts\activate" (
    echo Virtuální prostředí nebylo nalezeno. Vytvářím virtuální prostředí pomocí %PYTHON_EXE%...
    %PYTHON_EXE% -m venv venvTBM
    if errorlevel 1 (
        echo [CHYBA] Chyba při vytváření virtuálního prostředí.
        pause
        exit /b
    )
) else (
    echo Virtuální prostředí venvTBM nalezeno.
)

REM --- Aktivace virtuálního prostředí ---
call venvTBM\Scripts\activate

REM --- Instalace požadovaných balíčků ---
echo Instalace balíčků z requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo [CHYBA] Chyba při instalaci balíčků. Zkontrolujte requirements.txt.
    pause
    exit /b
)

REM --- Provedení databázových migrací ---
echo Provádím makemigrations...
python manage.py makemigrations
if errorlevel 1 (
    echo [CHYBA] Chyba při vytváření migrací.
    pause
    exit /b
)

echo Provádím migrate...
python manage.py migrate
if errorlevel 1 (
    echo [CHYBA] Chyba při provádění migrací.
    pause
    exit /b
)

echo Instalace byla úspěšná.
echo Nezapomeňte upravit SECRET_KEY a ALLOWED_HOSTS v souboru settings.py dle README.md.
pause