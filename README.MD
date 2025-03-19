# TicketBadgeManager

## Obsah

- [TicketBadgeManager](#ticketbadgemanager)
- [Screenshot aplikace](#screenshot-aplikace)
- [Před samotným spuštěním aplikace](#před-samotným-spuštěním-aplikace)
- [Spuštění aplikace pomocí .bat souborů](#spuštění-aplikace-pomocí-bat-souborů)
  - [install_app.bat](#install_appbat)
  - [start_server.bat](#start_serverbat)
  - [update_app.bat](#update_appbat)
- [Jak spustit aplikaci manuálně](#jak-spustit-aplikaci-manuálně)
  - [1. Naklonujte repozitář](#1-naklonujte-repozitář)
  - [2. Vytvoření virtuálního prostředí](#2-vytvoření-virtuálního-prostředí)
  - [3. Aktivace virtuálního prostředí](#3-aktivace-virtuálního-prostředí)
  - [4. Deaktivace virtuálního prostředí](#4-deaktivace-virtuálního-prostředí)
  - [5. Nainstalujte požadované balíčky](#5-nainstalujte-požadované-balíčky)
  - [6. Proveďte databázové migrace](#6-proveďte-databázové-migrace)
  - [7. Upravte soubor settings.py](#7-upravte-soubor-settingspy)
  - [8. Spusťte server](#8-spusťte-server)
  - [9. Otevřete prohlížeč](#9-otevřete-prohlížeč)
- [Jak aktualizovat aplikaci](#jak-aktualizovat-aplikaci)
- [Instalace a nastavení tiskáren - TSC TDP-225](#instalace-a-nastavení-tiskáren---tsc-tdp-225)
- [Konfigurace tisku](#konfigurace-tisku)
- [Plánované funkce - todo](#plánované-funkce---todo)

**TicketBadgeManager** je Django aplikace určená pro odbavování vstupenek a tisk visaček pro networkingové eventy na termo tiskárně TSC. 

Aplikace umožňuje importovat CSV se vstupenkami, provádět check-in pomocí QR kódů a tisknout štítek se jménem, příjmením a názvem společnosti.

Testováno na tiskárně **TSC TDP-225**.

Funguje zatím jen na Windows – využívá win32print.

## Screenshot aplikace

![Screenshot aplikace](/TBM_index.png)

## Před samotným spuštěním aplikace
- Nainstalovaný Python 3.11 – otestováno na 3.11; s verzí 3.12 byl problém s některými moduly – [Python 3.11.9](https://www.python.org/downloads/release/python-3119/). Při instalaci nezapomeňte zaškrtnout „Add Python to PATH“.
- Nainstalovaný Git, nebo možnost stáhnout repozitář jako ZIP – [Git](https://git-scm.com/downloads/win).
- Nainstalované tiskárny – správný název podle [Instalace a nastavení tiskáren - TSC TDP-225](https://github.com/kalus-msic/TicketBadgeManager/tree/main?tab=readme-ov-file#instalace-a-nastaven%C3%AD-tisk%C3%A1ren---tsc-tdp-225).
- Správně nastavený firewall – na PC, kde běží aplikace, musí být otevřen port, na kterém aplikace běží (výchozí 8000).
- **Windows (CMD run as administrator):** 

```bash
netsh advfirewall firewall add rule name="Django Web Server" protocol=TCP dir=in localport=8000 action=allow profile=private,domain
```


## Spuštění aplikace pomocí .bat souborů

Pro usnadnění spouštění a aktualizací aplikace jsme připravili tři .bat soubory, které můžete umístit do kořenové složky projektu:

- **install_app.bat** – Tento skript provede základní instalační kroky podle tohoto README. Vytvoří virtuální prostředí (pokud ještě neexistuje), nainstaluje požadované balíčky a provede databázové migrace.
- **start_server.bat** – Tento skript aktivuje virtuální prostředí a spustí server s SSL (příkaz `runsslserver`). Po spuštění se automaticky otevře výchozí prohlížeč na adrese `https://127.0.0.1:8000`.
- **update_app.bat** – Tento skript zkontroluje aktuálnost repozitáře, a pokud je nalezena nová verze, nabídne vám její stažení. V případě potvrzení provede `git pull`, aktivuje virtuální prostředí a spustí databázové migrace (`makemigrations` a `migrate`). Pokud uživatel aktualizaci zamítne, skript se ukončí bez provedení migrací.

## Jak spustit aplikaci manuálně
### 1. Naklonujte repozitář

```bash
git clone https://github.com/kalus-msic/TicketBadgeManager.git
cd TicketBadgeManager
```
**Poznámka:** Pokud váš systém používá příkaz `python3` místo `python`, nahraďte příkazy odpovídajícím způsobem.

### 2. Vytvoření virtuálního prostředí (pouze jednou)  
Při prvním spuštění si vytvořte virtuální prostředí:  

```bash
python -m venv venvTBM
```

---

### 3. Aktivace virtuálního prostředí (při každém spuštění projektu)  
Před spuštěním aplikace aktivujte virtuální prostředí podle svého systému:  

- **Windows (CMD):**  
  ```cmd
  venvTBM\Scripts\activate
  ```

- **Windows (PowerShell):**  
  Pokud dostanete chybu `"running scripts is disabled"`, povolte skripty dočasně pro toto okno:  
  ```powershell
  Set-ExecutionPolicy Unrestricted -Scope Process
  ```
  Poté aktivujte prostředí:  
  ```powershell
  venvTBM\Scripts\Activate.ps1
  ```

### 4. Deaktivace virtuálního prostředí  
Pokud chcete prostředí vypnout, stačí použít:  
```bash
deactivate
```

### 5. Nainstalujte požadované balíčky  

Než spustíte tento příkaz, **ujistěte se, že máte aktivované virtuální prostředí** (viz informace výše).  
Poznáte to podle toho, že na začátku příkazového řádku vidíte název virtuálního prostředí v závorkách, například:  

```
(venvTBM) $
```

Pokud virtuální prostředí není aktivní, **nejprve ho aktivujte** (viz krok 2).  

Jakmile je aktivní, nainstalujte požadované balíčky:  

```bash
pip install -r requirements.txt
```

### 6. Proveďte databázové migrace

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Upravte soubor settings.py – SECRET_KEY a ALLOWED_HOSTS
**Důležité:** Před spuštěním aplikace si změňte hodnotu `SECRET_KEY` v souboru `ticket_badge_manager/settings.py` na unikátní a bezpečnou hodnotu.  
Například můžete vygenerovat nový secret key pomocí příkazu:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```
```python
SECRET_KEY = 'nahodny_klic'
```
Dále do ALLOWED_HOSTS přidejte IP vašeho počítače, na kterém běží aplikace a jsou v něm připojeny tiskárny.
```python
ALLOWED_HOSTS = ['127.0.0.1', '192.x.x.x']
```

### 8. Spusťte server

```bash
python manage.py runsslserver 0.0.0.0:8000
```

Pokud při spuštění serveru narazíte na chybu, zkontrolujte, zda používáte správnou verzi Pythonu, na které byla aplikace testována (v našem případě **3.11.9**). Verzi Pythonu si můžete ověřit příkazem:

```bash
python --version
```

Pokud je nainstalovaná jiná verze, stáhněte si správnou verzi z odkazu výše. Následně musíte vytvořit virtuální prostředí se správnou verzí, například:

```bash
py -3.11 -m venv venvTBM311
venvTBM311\Scripts\activate
```

A pokračujte od bodu 5. 

### 9. Otevřete prohlížeč – pokud není specifikováno
```bash
https://127.0.0.1:8000/
```

## Jak aktualizovat aplikaci

Pokud si všimnete, že v repozitáři došlo k novým změnám (např. nová funkcionalita, opravy chyb, nové migrace či závislosti), doporučuji postupovat následovně:

1. **Aktualizace zdrojového kódu:**

   ```bash
   git pull origin main
   ```

2. **Instalace nových závislostí (pokud jsou přidány):**

   ```bash
   pip install -r requirements.txt
   ```

3. **Provedení databázových migrací:**

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Restartování serveru:**  
   Po aktualizaci kódu a migracích restartujte server, aby se změny projevily.

Tento postup zajistí, že vaše lokální verze aplikace bude aktuální a kompatibilní s novými změnami v repozitáři.

## Instalace a nastavení tiskáren - TSC TDP-225

Aktuálně je aplikace připravena pro tisk na až dvou tiskárnách.  
Na některých PC může dojít k problémům s automatickou instalací tiskárny – případně se doporučuje využít instalátoru ze stránek výrobce.  
Na testovacích stanicích jsem prováděl manuální přidání tiskárny s následným výběrem driveru TSC.inf – případně doplním další informace do README.md.

Během testování bylo zjištěno, že pro správnou funkčnost je nejlepší vybírat tiskárny podle jejich názvů, proto je potřeba mít před tiskem správně nastavené názvy tiskáren.  

**Windows 10**  
- Ovládací panely → Hardware a zvuk → Zařízení a tiskárny  
- Pravým klikem na TSC TDP-225 → Vlastnosti tiskárny → Obecné → změňte název na TDP-2251 (nebo TDP-2252)

**Windows 11**  
- Start → Tiskárny a skenery  
- Otevřít tiskárnu TSC TDP-225 → Vlastnosti tiskárny → Obecné → změňte název na TDP-2251 (nebo TDP-2252)

Výchozí tiskárna: TDP-2251  
Skener 1: TDP-2251  
Skener 2: TDP-2252

## Konfigurace tisku
**Poznámka:** Tisk je připraven pro štítky o velikosti 40x80 mm. Výchozí nastavení předpokládá, že se štítky tisknou vertikálně, přičemž celý obrázek štítku je vygenerován a poté otočen o 90 stupňů (viz funkce `create_label_image`), aby byl výsledný tisk správně orientován.

Tiskové parametry (např. šířka, výška štítku, DPI, density, contrast, název tiskárny, velikost fontu a cesty k fontům) jsou v současné verzi aplikace definovány přímo v souboru `views.py` (sekce věnovaná tiskárenským funkcím). Pokud si znalý uživatel přeje změnit výchozí nastavení tisku, musí ručně upravit následující proměnné:

- **PWIDTH** – šířka štítku (výchozí: `40`)
- **PHEIGHT** – výška štítku (výchozí: `80`)
- **DPI** – hustota tiskového rozlišení (výchozí: `200`)
- **DENSITY** – hustota tisku (výchozí: `15`)
- **CONTRAST** – prahová hodnota kontrastu (výchozí: `128`)
- **printerName** – výchozí název tiskárny (výchozí: `"TDP-225"`)
- **font_size** – počáteční velikost fontu při tisku (výchozí: `250`)
- **Cesty k fontům** – cesty k souborům fontů (`fonts/MontserratBold700.ttf` a `fonts/MontserratSemiBold600.ttf`)


## Plánované funkce - todo

- [ ] Schéma zapojení: Přidat schéma zapojení.
- [x] Dopsat README.md – chybí informace o HTTPS; je potřeba pro správnou funkci skeneru z ostatních stanic.
- [x] Lepší logování změn
- [ ] Přidat info o možnosti využití ngrok – odpadá potřeba vlastní lokální sítě; pomalejší odezva, ale možnost napojit aplikace prodejců vstupenek (ti.to).
- [x] Napojení na Eventee – při manuálním vytvoření vstupenky v TBM přidat i do Eventee.
- [ ] Dvoujazyčná podpora.
- [x] Ošetřit některé chyby.
- [x] Zlepšit výpis stavů – místo využití příkazu print zobrazovat informace přímo v aplikaci.
