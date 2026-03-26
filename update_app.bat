@echo off
setlocal enabledelayedexpansion
title TicketBadgeManager - Aktualizace

echo ============================================================
echo  TicketBadgeManager - Aktualizace aplikace
echo ============================================================
echo.

REM --- Kontrola aktualizaci v repozitari ---
echo Kontroluji aktualizace...
git fetch --all --quiet
if errorlevel 1 (
    echo [UPOZORNENI] Git fetch selhal. Zkontrolujte pripojeni k internetu.
)

REM Zjisteni aktualni vetve
for /f "tokens=*" %%i in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%i

REM Pokud uzivatel neni na main, nabidni prepnuti
if not "%BRANCH%"=="main" (
    echo [UPOZORNENI] Jste na vetvi '%BRANCH%', nikoliv na 'main'.
    choice /m "Prepnout na stabilni vetev 'main' a aktualizovat? (A/N)"
    if errorlevel 2 (
        echo Aktualizace zrusena.
        goto :end
    ) else (
        echo Prepinani na main...
        git checkout main
        if errorlevel 1 (
            echo [CHYBA] Prepnuti na main selhalo.
            goto :end
        )
        set BRANCH=main
    )
)

echo Aktualni vetev: main

REM Zjisteni hashe lokalniho commitu a vzdalene vetve
for /f "tokens=*" %%i in ('git rev-parse HEAD') do set LOCAL=%%i

set REMOTE=
for /f "tokens=*" %%i in ('git rev-parse origin/main 2^>nul') do set REMOTE=%%i

if "!REMOTE!"=="" (
    echo [UPOZORNENI] Vzdalena vetev origin/main nenalezena. Preskakuji kontrolu aktualizaci.
    goto :migrations
)

if "%LOCAL%"=="!REMOTE!" (
    echo Aplikace je aktualni. Zadne aktualizace nejsou dostupne.

    REM Zkontroluj, zda dev obsahuje novejsi verzi (beta)
    set DEV_REMOTE=
    for /f "tokens=*" %%i in ('git rev-parse origin/dev 2^>nul') do set DEV_REMOTE=%%i
    if not "!DEV_REMOTE!"=="" (
        if not "!LOCAL!"=="!DEV_REMOTE!" (
            echo.
            echo [BETA] Je dostupna novejsi vyvojova verze ^(vetev 'dev'^).
            choice /m "Chcete prepnout na beta verzi? Pozor: muze obsahovat chyby. (A/N)"
            if errorlevel 2 (
                echo Zustavame na stabilni verzi main.
            ) else (
                echo Prepinani na dev...
                git checkout dev
                git pull origin dev
            )
        )
    )
    goto :migrations
) else (
    echo Nalezeny aktualizace.
    choice /m "Chcete stahnout aktualizace? (A/N)"
    if errorlevel 2 (
        echo Aktualizace nebyla provedena.
        goto :end
    ) else (
        echo Stahuji aktualizace...
        git pull origin main
        if errorlevel 1 (
            echo [CHYBA] Git pull selhal.
            goto :end
        )
    )
)

:migrations
echo.
echo --- Aktivace virtualniho prostredi ---
if exist venvTBM\Scripts\activate.bat (
    call venvTBM\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else if exist venvTBM\Scripts\activate (
    call venvTBM\Scripts\activate
) else (
    echo [CHYBA] Virtualni prostredi nenalezeno. Spustte nejdrive install_app.bat.
    goto :end
)

echo.
echo --- Aktualizace zavislosti ---
call python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [UPOZORNENI] Aktualizace zavislosti selhala. Zkontrolujte internet nebo pip.
)

echo.
echo --- Databazove migrace ---
call python manage.py makemigrations
if errorlevel 1 (
    echo [CHYBA] makemigrations selhal. Aktualizace nebyla dokoncena.
    goto :end
)

call python manage.py migrate
if errorlevel 1 (
    echo [CHYBA] migrate selhal. Aktualizace nebyla dokoncena.
    goto :end
)

echo.
echo --- Preklady ---
call python manage.py compilemessages
if errorlevel 1 (
    echo [UPOZORNENI] Kompilace prekladu selhala.
)

echo.
echo --- Staticke soubory ---
call python manage.py collectstatic --noinput
if errorlevel 1 (
    echo [UPOZORNENI] collectstatic selhal.
)

echo.
echo --- SSL certifikat ---
if not exist "cert.pem" (
    echo [INFO] cert.pem nenalezen. Bude vygenerovan pri prvnim spusteni start_server.bat.
)

echo.
echo ============================================================
echo  Aktualizace dokoncena.
echo ============================================================
echo.
echo POZNAMKA: Pokud jde o prvni spusteni po aktualizaci na verzi s vice akcemi,
echo           byla automaticky vytvorena vychozi akce "Vychozi akce".
echo           Prejmenujte ji v aplikaci dle potreby.

:end
echo.
pause
