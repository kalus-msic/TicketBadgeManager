# TicketBadgeManager - Translation Guide

## How to compile translations

After updating .po files, you need to compile them to .mo files:

```bash
python manage.py compilemessages
```

Or use the standalone script (doesn't require Django):
```bash
python compile_mo_files.py
```

## All translated strings

### Dashboard (index.html)
- Dashboard → Přehled
- Manage and validate tickets for your event → Spravujte a ověřujte vstupenky pro vaši akci
- Scan Tickets → Skenovat vstupenky
- Create New Ticket → Vytvořit novou vstupenku
- Kiosk Mode → Kiosek mód
- Total Tickets → Celkem vstupenek
- Remaining → Zbývá
- Ready to check-in → Připraveno k odbavení
- Checked In → Odbaveno
- complete → dokončeno
- Last Hour → Poslední hodina
- Check-in rate → Rychlost odbavení
- Recent Check-ins → Nedávná odbavení
- Actions → Akce
- Ticket Number → Číslo vstupenky
- Name → Jméno
- Company → Firma
- Checked-in → Odbaveno
- No recent check-ins → Žádná nedávná odbavení

### Scanner (scanner.html)
- Scan Ticket → Skenovat vstupenku
- Active Scanner → Aktivní skener
- Search VALID tickets by name and press Enter (or use scanner below) → Hledejte PLATNÉ vstupenky podle jména a stiskněte Enter (nebo použijte skener níže)
- Search → Hledat
- No tickets found → Nenalezeny žádné vstupenky
- Verify & Print → Ověřit a tisknout
- Search error → Chyba vyhledávání
- Back to Tickets → Zpět na vstupenky
- View Ticket details → Zobrazit detaily vstupenky

### Ticket List (ticket_list.html)
- Tickets → Vstupenky
- Create New Ticket → Vytvořit novou vstupenku
- Export Tickets → Exportovat vstupenky
- Total Tickets → Celkem vstupenek
- Valid Tickets → Platné vstupenky
- Used Tickets → Použité vstupenky
- Search by name, company, or QR code → Hledat podle jména, firmy nebo QR kódu
- Clear → Vymazat
- All Statuses → Všechny stavy
- Valid → Platná
- Used → Použitá
- Cancelled → Zrušená
- Status → Stav
- View details → Zobrazit detaily
- Verify ticket & print label → Ověřit vstupenku a vytisknout štítek
- First → První
- Previous → Předchozí
- Next → Další
- Last → Poslední

### Import (import.html)
- Import Tickets → Import vstupenek
- CSV Import → CSV Import
- Upload CSV File → Nahrát CSV soubor
- Replace all existing tickets → Nahradit všechny existující vstupenky
- Add to existing tickets → Přidat k existujícím vstupenkám
- Download sample CSV → Stáhnout vzorový CSV
- Choose file → Vybrat soubor
- Import → Importovat
- File uploaded successfully → Soubor úspěšně nahrán

### Settings (settings.html)
- Settings → Nastavení
- Eventee API Token → Eventee API Token
- Test Connection → Test připojení
- Required Ticket Fields → Povinná pole vstupenky
- Required Fields → Povinná pole
- Save Settings → Uložit nastavení
- Delete All Data → Smazat všechna data
- Delete All Check-ins → Smazat všechna odbavení
- Update Token → Aktualizovat token
- Settings updated successfully → Nastavení úspěšně aktualizováno
- All data deleted successfully → Všechna data úspěšně smazána
- All check-ins deleted successfully → Všechna odbavení úspěšně smazána

### Kiosk (kiosk.html)
- Event Check-in → Odbavení na akci
- Please scan your ticket QR code → Prosím naskenujte QR kód vaší vstupenky
- Ready to scan... → Připraveno ke skenování...
- Welcome! → Vítejte!
- Having trouble? Please ask our staff for assistance. → Máte potíže? Požádejte náš personál o pomoc.
- Please see our staff for assistance → Prosím obraťte se na náš personál
- Badge is being printed → Visačka se tiskne
- Camera access denied. Please allow camera access and refresh the page. → Přístup ke kameře byl odepřen. Povolte přístup ke kameře a obnovte stránku.

### Logs (log.html)
- Logs → Protokoly
- Event Logs → Protokoly událostí
- Delete All Logs → Smazat všechny protokoly
- Time → Čas
- Ticket → Vstupenka
- Event Type → Typ události
- Message → Zpráva
- Check-In → Odbavení
- Update → Aktualizace
- Other → Jiné
- Error → Chyba
- System → Systém
- No logs found → Nenalezeny žádné protokoly

### Special Labels (special_labels.html)
- Special Labels → Speciální štítky
- Print Special Labels → Tisk speciálních štítků
- Print labels for Press, Host, Staff, etc. → Tisk štítků pro Press, Host, Staff atd.
- Quantity → Množství
- Printer → Tiskárna
- Printer 1 → Tiskárna 1
- Printer 2 → Tiskárna 2
- Print → Tisknout
- Print Labels → Tisknout štítky
- Special labels printed successfully → Speciální štítky úspěšně vytištěny

### Messages
- Ticket created successfully → Vstupenka úspěšně vytvořena
- Ticket updated successfully → Vstupenka úspěšně aktualizována
- Ticket deleted successfully → Vstupenka úspěšně smazána
- tickets reset successfully → vstupenky úspěšně resetovány
- tickets deleted successfully → vstupenky úspěšně smazány
- No tickets selected → Nebyly vybrány žádné vstupenky
- Check-in successful → Odbavení úspěšné
- Ticket not found → Vstupenka nenalezena
- Already used → Již použitá
- Ticket is cancelled → Vstupenka je zrušená

## Missing translations that need to be added to templates

If you find any untranslated text in the application, wrap it with `{% trans "Text" %}` tag and add the translation to both .po files.