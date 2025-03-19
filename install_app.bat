@echo off
REM --- Kontrola, zda se nacházíme v kořenovém adresáři projektu ---
if not exist "manage.py" (
    echo Soubor manage.py nebyl nalezen. Spusťte tento skript v kořenovém adresáři projektu.
    pause
    exit /b
)

REM --- Vytvoření virtuálního prostředí, pokud ještě neexistuje ---
if not exist "venvTBM\Scripts\activate" (
    echo Virtuální prostředí nebylo nalezeno. Vytvářím virtuální prostředí...
    python -m venv venvTBM
    if errorlevel 1 (
        echo Chyba při vytváření virtuálního prostředí. Ujistěte se, že máte nainstalovaný Python.
        pause
        exit /b
    )
) else (
    echo Virtuální prostředí venvTBM nalezeno.
)

REM --- Aktivace virtuálního prostředí ---
call venvTBM\Scripts\activate

REM --- Instalace potřebných balíčků ---
echo Instalace balíčků z requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo Chyba při instalaci balíčků. Zkontrolujte requirements.txt.
    pause
    exit /b
)

REM --- Provedení databázových migrací ---
echo Provádím makemigrations...
python manage.py makemigrations
if errorlevel 1 (
    echo Chyba při vytváření migrací.
    pause
    exit /b
)

echo Provádím migrate...
python manage.py migrate
if errorlevel 1 (
    echo Chyba při provádění migrací.
    pause
    exit /b
)

echo Instalace byla úspěšná.
echo Nezapomeňte upravit SECRET_KEY a ALLOWED_HOSTS v souboru settings.py dle poznámek v README.md.
pause