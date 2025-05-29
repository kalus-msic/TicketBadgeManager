#!/usr/bin/env python3
"""
Script to add missing translations to .po files
"""

# New translations to add to CS file
CS_ADDITIONS = """
# Scanner page
msgid "Scan Ticket"
msgstr "Skenovat vstupenku"

msgid "Active Scanner"
msgstr "Aktivní skener"

msgid "Search VALID tickets by name and press Enter (or use scanner below)"
msgstr "Hledejte PLATNÉ vstupenky podle jména a stiskněte Enter (nebo použijte skener níže)"

msgid "Back to Tickets"
msgstr "Zpět na vstupenky"

msgid "View Ticket details"
msgstr "Zobrazit detaily vstupenky"

# Dashboard/Index additions
msgid "Ready to check-in"
msgstr "Připraveno k odbavení"

msgid "complete"
msgstr "dokončeno"

msgid "Check-in rate"
msgstr "Rychlost odbavení"

msgid "Remaining"
msgstr "Zbývá"

msgid "Checked In"
msgstr "Odbaveno"

msgid "Last Hour"
msgstr "Poslední hodina"

msgid "Recent Check-ins"
msgstr "Nedávná odbavení"

# Ticket list additions
msgid "Tickets"
msgstr "Vstupenky"

msgid "Export Tickets"
msgstr "Exportovat vstupenky"

msgid "Total Tickets"
msgstr "Celkem vstupenek"

msgid "Valid Tickets"
msgstr "Platné vstupenky"

msgid "Used Tickets"
msgstr "Použité vstupenky"

msgid "Search by name, company, or QR code"
msgstr "Hledat podle jména, firmy nebo QR kódu"

msgid "Clear"
msgstr "Vymazat"

msgid "All Statuses"
msgstr "Všechny stavy"

msgid "No tickets found"
msgstr "Nenalezeny žádné vstupenky"

msgid "First"
msgstr "První"

msgid "Previous"
msgstr "Předchozí"

msgid "Next"
msgstr "Další"

msgid "Last"
msgstr "Poslední"

msgid "View details"
msgstr "Zobrazit detaily"

msgid "Verify ticket & print label"
msgstr "Ověřit vstupenku a vytisknout štítek"

# Import page
msgid "Import Tickets"
msgstr "Import vstupenek"

msgid "Upload CSV File"
msgstr "Nahrát CSV soubor"

msgid "Replace all existing tickets"
msgstr "Nahradit všechny existující vstupenky"

msgid "Add to existing tickets"
msgstr "Přidat k existujícím vstupenkám"

msgid "Download sample CSV"
msgstr "Stáhnout vzorový CSV"

msgid "Choose file"
msgstr "Vybrat soubor"

msgid "CSV Import"
msgstr "CSV Import"

msgid "File uploaded successfully"
msgstr "Soubor úspěšně nahrán"

# Settings additions
msgid "Eventee API Token"
msgstr "Eventee API Token"

msgid "Test Connection"
msgstr "Test připojení"

msgid "Required Ticket Fields"
msgstr "Povinná pole vstupenky"

msgid "Save Settings"
msgstr "Uložit nastavení"

msgid "Delete All Data"
msgstr "Smazat všechna data"

msgid "Delete All Check-ins"
msgstr "Smazat všechna odbavení"

msgid "Update Token"
msgstr "Aktualizovat token"

msgid "Required Fields"
msgstr "Povinná pole"

msgid "Settings updated successfully"
msgstr "Nastavení úspěšně aktualizováno"

msgid "All data deleted successfully"
msgstr "Všechna data úspěšně smazána"

msgid "All check-ins deleted successfully"
msgstr "Všechna odbavení úspěšně smazána"

# Kiosk mode
msgid "Event Check-in"
msgstr "Odbavení na akci"

msgid "Please scan your ticket QR code"
msgstr "Prosím naskenujte QR kód vaší vstupenky"

msgid "Ready to scan..."
msgstr "Připraveno ke skenování..."

msgid "Welcome!"
msgstr "Vítejte!"

msgid "Having trouble? Please ask our staff for assistance."
msgstr "Máte potíže? Požádejte náš personál o pomoc."

msgid "Please see our staff for assistance"
msgstr "Prosím obraťte se na náš personál"

msgid "Badge is being printed"
msgstr "Visačka se tiskne"

msgid "Camera access denied. Please allow camera access and refresh the page."
msgstr "Přístup ke kameře byl odepřen. Povolte přístup ke kameře a obnovte stránku."

# Logs
msgid "Event Logs"
msgstr "Protokoly událostí"

msgid "Delete All Logs"
msgstr "Smazat všechny protokoly"

msgid "Time"
msgstr "Čas"

msgid "Event Type"
msgstr "Typ události"

msgid "Message"
msgstr "Zpráva"

msgid "No logs found"
msgstr "Nenalezeny žádné protokoly"

# Additional messages
msgid "Special labels printed successfully"
msgstr "Speciální štítky úspěšně vytištěny"

msgid "Printer"
msgstr "Tiskárna"

msgid "Printer 1"
msgstr "Tiskárna 1"

msgid "Printer 2"
msgstr "Tiskárna 2"
"""

# New translations to add to EN file (same as msgid)
EN_ADDITIONS = """
# Scanner page
msgid "Scan Ticket"
msgstr "Scan Ticket"

msgid "Active Scanner"
msgstr "Active Scanner"

msgid "Search VALID tickets by name and press Enter (or use scanner below)"
msgstr "Search VALID tickets by name and press Enter (or use scanner below)"

msgid "Back to Tickets"
msgstr "Back to Tickets"

msgid "View Ticket details"
msgstr "View Ticket details"

# Dashboard/Index additions
msgid "Ready to check-in"
msgstr "Ready to check-in"

msgid "complete"
msgstr "complete"

msgid "Check-in rate"
msgstr "Check-in rate"

msgid "Remaining"
msgstr "Remaining"

msgid "Checked In"
msgstr "Checked In"

msgid "Last Hour"
msgstr "Last Hour"

msgid "Recent Check-ins"
msgstr "Recent Check-ins"

# Ticket list additions
msgid "Tickets"
msgstr "Tickets"

msgid "Export Tickets"
msgstr "Export Tickets"

msgid "Total Tickets"
msgstr "Total Tickets"

msgid "Valid Tickets"
msgstr "Valid Tickets"

msgid "Used Tickets"
msgstr "Used Tickets"

msgid "Search by name, company, or QR code"
msgstr "Search by name, company, or QR code"

msgid "Clear"
msgstr "Clear"

msgid "All Statuses"
msgstr "All Statuses"

msgid "No tickets found"
msgstr "No tickets found"

msgid "First"
msgstr "First"

msgid "Previous"
msgstr "Previous"

msgid "Next"
msgstr "Next"

msgid "Last"
msgstr "Last"

msgid "View details"
msgstr "View details"

msgid "Verify ticket & print label"
msgstr "Verify ticket & print label"

# Import page
msgid "Import Tickets"
msgstr "Import Tickets"

msgid "Upload CSV File"
msgstr "Upload CSV File"

msgid "Replace all existing tickets"
msgstr "Replace all existing tickets"

msgid "Add to existing tickets"
msgstr "Add to existing tickets"

msgid "Download sample CSV"
msgstr "Download sample CSV"

msgid "Choose file"
msgstr "Choose file"

msgid "CSV Import"
msgstr "CSV Import"

msgid "File uploaded successfully"
msgstr "File uploaded successfully"

# Settings additions
msgid "Eventee API Token"
msgstr "Eventee API Token"

msgid "Test Connection"
msgstr "Test Connection"

msgid "Required Ticket Fields"
msgstr "Required Ticket Fields"

msgid "Save Settings"
msgstr "Save Settings"

msgid "Delete All Data"
msgstr "Delete All Data"

msgid "Delete All Check-ins"
msgstr "Delete All Check-ins"

msgid "Update Token"
msgstr "Update Token"

msgid "Required Fields"
msgstr "Required Fields"

msgid "Settings updated successfully"
msgstr "Settings updated successfully"

msgid "All data deleted successfully"
msgstr "All data deleted successfully"

msgid "All check-ins deleted successfully"
msgstr "All check-ins deleted successfully"

# Kiosk mode
msgid "Event Check-in"
msgstr "Event Check-in"

msgid "Please scan your ticket QR code"
msgstr "Please scan your ticket QR code"

msgid "Ready to scan..."
msgstr "Ready to scan..."

msgid "Welcome!"
msgstr "Welcome!"

msgid "Having trouble? Please ask our staff for assistance."
msgstr "Having trouble? Please ask our staff for assistance."

msgid "Please see our staff for assistance"
msgstr "Please see our staff for assistance"

msgid "Badge is being printed"
msgstr "Badge is being printed"

msgid "Camera access denied. Please allow camera access and refresh the page."
msgstr "Camera access denied. Please allow camera access and refresh the page."

# Logs
msgid "Event Logs"
msgstr "Event Logs"

msgid "Delete All Logs"
msgstr "Delete All Logs"

msgid "Time"
msgstr "Time"

msgid "Event Type"
msgstr "Event Type"

msgid "Message"
msgstr "Message"

msgid "No logs found"
msgstr "No logs found"

# Additional messages
msgid "Special labels printed successfully"
msgstr "Special labels printed successfully"

msgid "Printer"
msgstr "Printer"

msgid "Printer 1"
msgstr "Printer 1"

msgid "Printer 2"
msgstr "Printer 2"
"""

if __name__ == "__main__":
    # Read current CS file
    with open('locale/cs/LC_MESSAGES/django.po', 'r', encoding='utf-8') as f:
        cs_content = f.read()
    
    # Read current EN file
    with open('locale/en/LC_MESSAGES/django.po', 'r', encoding='utf-8') as f:
        en_content = f.read()
    
    # Append new translations to CS file
    with open('locale/cs/LC_MESSAGES/django.po', 'a', encoding='utf-8') as f:
        f.write("\n" + CS_ADDITIONS)
    
    # Append new translations to EN file
    with open('locale/en/LC_MESSAGES/django.po', 'a', encoding='utf-8') as f:
        f.write("\n" + EN_ADDITIONS)
    
    print("✅ Added translations to .po files")
    print("Now run: python manage.py compilemessages")