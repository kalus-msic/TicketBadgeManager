# TicketBadgeManager

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

## Jak spustit aplikaci

### 1. Naklonujte repozitář

```bash
git clone https://github.com/kalus-msic/TicketBadgeManager.git
cd TicketBadgeManager
```
**Poznámka:** Pokud váš systém používá příkaz `python3` místo `python`, nahraďte příkazy odpovídajícím způsobem.

### 2. Vytvořte a aktivujte virtuální prostředí (doporučeno)

```bash
python -m venv venv
venv\Scripts\activate  
```

### 3. Nainstalujte požadované balíčky

```bash
pip install -r requirements.txt
```

### 4. Proveďte databázové migrace

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Upravte soubor settings.py – SECRET_KEY a ALLOWED_HOSTS
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

### 6. Spusťte server

```bash
python manage.py runsslserver 0.0.0.0:8000
```

### 7. Otevřete prohlížeč – pokud není specifikováno
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

## Plánované funkce - todo

- [ ] Schéma zapojení: Přidat schéma zapojení.
- [x] Dopsat README.md – chybí informace o HTTPS; je potřeba pro správnou funkci skeneru z ostatních stanic.
- [ ] Přidat info o možnosti využití ngrok – odpadá potřeba vlastní lokální sítě; pomalejší odezva, ale možnost napojit aplikace prodejců vstupenek (ti.to).
- [ ] Napojení na Eventee – při manuálním vytvoření vstupenky v TBM přidat i do Eventee.
- [ ] Dvoujazyčná podpora.
- [ ] Ošetřit některé chyby.
- [ ] Zlepšit výpis stavů – místo využití příkazu print zobrazovat informace přímo v aplikaci.
