#!/usr/bin/env python3
"""Check for duplicate msgid entries in .po files."""

import sys
import re

def check_po_file(filename):
    """Check a .po file for duplicate msgid entries."""
    msgids = {}
    duplicates = []
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    current_msgid = None
    for i, line in enumerate(lines):
        if line.startswith('msgid "'):
            # Extract msgid
            match = re.match(r'msgid "(.*)"', line)
            if match:
                current_msgid = match.group(1)
                if current_msgid in msgids:
                    duplicates.append({
                        'msgid': current_msgid,
                        'first_line': msgids[current_msgid] + 1,
                        'duplicate_line': i + 1
                    })
                else:
                    msgids[current_msgid] = i
    
    return duplicates

if __name__ == '__main__':
    po_file = '/home/adamko/mkal/TicketBadgeManager/locale/cs/LC_MESSAGES/django.po'
    duplicates = check_po_file(po_file)
    
    if duplicates:
        print(f"Found {len(duplicates)} duplicate(s):")
        for dup in duplicates:
            print(f"  '{dup['msgid']}' - first at line {dup['first_line']}, duplicate at line {dup['duplicate_line']}")
        sys.exit(1)
    else:
        print("No duplicates found!")
        sys.exit(0)