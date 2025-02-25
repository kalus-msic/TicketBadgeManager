# TicketBadgeManager

**TicketBadgeManager** je Django aplikace určená pro odbavování vstupenek a tisk visaček pro networkingové eventy.  
Aplikace umožňuje importovat CSV se vstupenkami, provádět check-in pomocí QR kódů a tisknout jména, příjmení a název společnosti na termo tiskárnách.

## 🚀 Jak spustit aplikaci

### 1.️Naklonujte repozitář

```bash
git clone https://github.com/kalus-msic/TicketBadgeManager.git
cd TicketBadgeManager
```
**Poznámka:** Pokud váš systém používá příkaz `python3` místo `python`, nahraďte příkazy odpovídajícím způsobem.
### 2.Vytvořte a aktivujte virtuální prostředí (doporučeno)

```bash
python -m venv venv
source venv/bin/activate  # Na Windows: venv\Scripts\activate
```

### 3. Nainstalujte e požadované balíčky

```bash
pip install -r requirements.txt
```

### 4. Proveďte databázové migrace

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Spusťte server

```bash
python manage.py runserver
```

### 6. Otevřete prohlížeč - pokud není specifikováno 
```bash
http://127.0.0.1:8000/
```
