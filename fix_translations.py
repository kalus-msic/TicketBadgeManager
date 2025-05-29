#!/usr/bin/env python3
"""
Script to add translation tags to all untranslated strings in templates
"""
import os
import re

# Dictionary of all strings that need translation
TRANSLATIONS_NEEDED = {
    # Index page
    "Ready to check-in": "Ready to check-in",
    "complete": "complete",
    "Check-in rate": "Check-in rate",
    
    # Scanner page  
    "Scan Ticket": "Scan Ticket",
    "Active Scanner": "Active Scanner",
    "Search VALID tickets by name and press Enter (or use scanner below)": "Search VALID tickets by name and press Enter (or use scanner below)",
    
    # Ticket list
    "Tickets": "Tickets", 
    "Create New Ticket": "Create New Ticket",
    "Export Tickets": "Export Tickets",
    "Total Tickets": "Total Tickets",
    "Valid Tickets": "Valid Tickets", 
    "Used Tickets": "Used Tickets",
    "Search by name, company, or QR code": "Search by name, company, or QR code",
    "Search": "Search",
    "Clear": "Clear",
    "All Statuses": "All Statuses",
    "Valid": "Valid",
    "Used": "Used", 
    "Cancelled": "Cancelled",
    "Actions": "Actions",
    "Ticket Number": "Ticket Number",
    "Name": "Name",
    "Company": "Company",
    "Status": "Status",
    "Checked-in": "Checked-in",
    "No tickets found": "No tickets found",
    "First": "First",
    "Previous": "Previous", 
    "Next": "Next",
    "Last": "Last",
    
    # Messages
    "Ticket created successfully": "Ticket created successfully",
    "Ticket updated successfully": "Ticket updated successfully",
    "Ticket deleted successfully": "Ticket deleted successfully",
    "tickets reset successfully": "tickets reset successfully",
    "No tickets selected": "No tickets selected",
    "File uploaded successfully": "File uploaded successfully",
    "Settings updated successfully": "Settings updated successfully",
    "All data deleted successfully": "All data deleted successfully",
    "All check-ins deleted successfully": "All check-ins deleted successfully",
    "Special labels printed successfully": "Special labels printed successfully",
    
    # Import page
    "Import Tickets": "Import Tickets",
    "Upload CSV File": "Upload CSV File",
    "Replace all existing tickets": "Replace all existing tickets",
    "Add to existing tickets": "Add to existing tickets",
    "Download sample CSV": "Download sample CSV",
    
    # Settings
    "Settings": "Settings",
    "Eventee API Token": "Eventee API Token",
    "Test Connection": "Test Connection",
    "Required Ticket Fields": "Required Ticket Fields",
    "Save Settings": "Save Settings",
    "Delete All Data": "Delete All Data",
    "Delete All Check-ins": "Delete All Check-ins",
    
    # Kiosk
    "Event Check-in": "Event Check-in",
    "Please scan your ticket QR code": "Please scan your ticket QR code",
    "Ready to scan...": "Ready to scan...",
    "Welcome!": "Welcome!",
    "Having trouble? Please ask our staff for assistance.": "Having trouble? Please ask our staff for assistance.",
    "Please see our staff for assistance": "Please see our staff for assistance",
    "Badge is being printed": "Badge is being printed",
}

# Czech translations
CZECH_TRANSLATIONS = {
    # Index page
    "Ready to check-in": "Připraveno k odbavení",
    "complete": "dokončeno",
    "Check-in rate": "Rychlost odbavení",
    "Remaining": "Zbývá",
    "Checked In": "Odbaveno",
    "Last Hour": "Poslední hodina",
    "Recent Check-ins": "Nedávná odbavení",
    
    # Scanner page
    "Scan Ticket": "Skenovat vstupenku",
    "Active Scanner": "Aktivní skener",
    "Search VALID tickets by name and press Enter (or use scanner below)": "Hledejte PLATNÉ vstupenky podle jména a stiskněte Enter (nebo použijte skener níže)",
    "Back to Tickets": "Zpět na vstupenky",
    "View Ticket details": "Zobrazit detaily vstupenky",
    
    # Ticket list
    "Tickets": "Vstupenky",
    "Create New Ticket": "Vytvořit novou vstupenku",
    "Export Tickets": "Exportovat vstupenky",
    "Total Tickets": "Celkem vstupenek",
    "Valid Tickets": "Platné vstupenky",
    "Used Tickets": "Použité vstupenky",
    "Search by name, company, or QR code": "Hledat podle jména, firmy nebo QR kódu",
    "Search": "Hledat",
    "Clear": "Vymazat",
    "All Statuses": "Všechny stavy",
    "Valid": "Platná",
    "Used": "Použitá",
    "Cancelled": "Zrušená",
    "Actions": "Akce",
    "Ticket Number": "Číslo vstupenky",
    "Name": "Jméno",
    "Company": "Firma",
    "Status": "Stav",
    "Checked-in": "Odbaveno",
    "No tickets found": "Nenalezeny žádné vstupenky",
    "First": "První",
    "Previous": "Předchozí",
    "Next": "Další",
    "Last": "Poslední",
    "View details": "Zobrazit detaily",
    "Verify ticket & print label": "Ověřit vstupenku a vytisknout štítek",
    
    # Messages
    "Ticket created successfully": "Vstupenka úspěšně vytvořena",
    "Ticket updated successfully": "Vstupenka úspěšně aktualizována", 
    "Ticket deleted successfully": "Vstupenka úspěšně smazána",
    "tickets reset successfully": "vstupenky úspěšně resetovány",
    "No tickets selected": "Nebyly vybrány žádné vstupenky",
    "File uploaded successfully": "Soubor úspěšně nahrán",
    "Settings updated successfully": "Nastavení úspěšně aktualizováno",
    "All data deleted successfully": "Všechna data úspěšně smazána",
    "All check-ins deleted successfully": "Všechna odbavení úspěšně smazána",
    "Special labels printed successfully": "Speciální štítky úspěšně vytištěny",
    "Check-in successful": "Odbavení úspěšné",
    "Ticket not found": "Vstupenka nenalezena",
    "Already used": "Již použitá",
    "Ticket is cancelled": "Vstupenka je zrušená",
    
    # Import page
    "Import Tickets": "Import vstupenek",
    "Upload CSV File": "Nahrát CSV soubor",
    "Replace all existing tickets": "Nahradit všechny existující vstupenky",
    "Add to existing tickets": "Přidat k existujícím vstupenkám",
    "Download sample CSV": "Stáhnout vzorový CSV",
    "Choose file": "Vybrat soubor",
    "Import": "Importovat",
    "CSV Import": "CSV Import",
    
    # Settings
    "Settings": "Nastavení",
    "Eventee API Token": "Eventee API Token",
    "Test Connection": "Test připojení",
    "Required Ticket Fields": "Povinná pole vstupenky",
    "Save Settings": "Uložit nastavení",
    "Delete All Data": "Smazat všechna data",
    "Delete All Check-ins": "Smazat všechna odbavení",
    "Update Token": "Aktualizovat token",
    "Required Fields": "Povinná pole",
    
    # Kiosk
    "Event Check-in": "Odbavení na akci",
    "Please scan your ticket QR code": "Prosím naskenujte QR kód vaší vstupenky",
    "Ready to scan...": "Připraveno ke skenování...",
    "Welcome!": "Vítejte!",
    "Having trouble? Please ask our staff for assistance.": "Máte potíže? Požádejte náš personál o pomoc.",
    "Please see our staff for assistance": "Prosím obraťte se na náš personál",
    "Badge is being printed": "Visačka se tiskne",
    "Camera access denied. Please allow camera access and refresh the page.": "Přístup ke kameře byl odepřen. Povolte přístup ke kameře a obnovte stránku.",
    
    # Special labels
    "Special Labels": "Speciální štítky",
    "Print Special Labels": "Tisk speciálních štítků",
    "Print labels for Press, Host, Staff, etc.": "Tisk štítků pro Press, Host, Staff atd.",
    "Quantity": "Množství",
    "Printer": "Tiskárna",
    "Print": "Tisknout",
    
    # Logs
    "Logs": "Protokoly",
    "Event Logs": "Protokoly událostí",
    "Delete All Logs": "Smazat všechny protokoly",
    "Time": "Čas",
    "Ticket": "Vstupenka",
    "Event Type": "Typ události",
    "Message": "Zpráva",
    "Check-In": "Odbavení",
    "Update": "Aktualizace",
    "Other": "Jiné",
    "Error": "Chyba",
    "System": "Systém",
    "No logs found": "Nenalezeny žádné protokoly",
}

if __name__ == "__main__":
    print("Translation mappings prepared.")
    print(f"Total English strings: {len(TRANSLATIONS_NEEDED)}")
    print(f"Total Czech translations: {len(CZECH_TRANSLATIONS)}")