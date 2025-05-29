#!/usr/bin/env python3
"""
Compile .po files to .mo files
This script can be run without Django installed
"""
import os
import subprocess
import sys

def compile_po_files():
    """Compile all .po files to .mo files"""
    locale_dir = 'locale'
    
    # Find all .po files
    po_files = []
    for root, dirs, files in os.walk(locale_dir):
        for file in files:
            if file.endswith('.po'):
                po_files.append(os.path.join(root, file))
    
    if not po_files:
        print("No .po files found!")
        return False
    
    print(f"Found {len(po_files)} .po file(s) to compile")
    
    # Try to find msgfmt command
    msgfmt_cmd = None
    for cmd in ['msgfmt', 'msgfmt.exe', '/usr/bin/msgfmt']:
        try:
            subprocess.run([cmd, '--version'], capture_output=True, check=True)
            msgfmt_cmd = cmd
            break
        except:
            continue
    
    if not msgfmt_cmd:
        print("ERROR: msgfmt command not found!")
        print("Please install gettext:")
        print("  - Windows: https://mlocati.github.io/articles/gettext-iconv-windows.html")
        print("  - Linux: sudo apt-get install gettext")
        print("  - macOS: brew install gettext")
        return False
    
    # Compile each .po file
    success_count = 0
    for po_file in po_files:
        mo_file = po_file.replace('.po', '.mo')
        print(f"Compiling {po_file} -> {mo_file}")
        
        try:
            result = subprocess.run([msgfmt_cmd, '-o', mo_file, po_file], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"  ✅ Success")
                success_count += 1
            else:
                print(f"  ❌ Error: {result.stderr}")
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
    
    print(f"\nCompiled {success_count}/{len(po_files)} files successfully")
    return success_count == len(po_files)

if __name__ == "__main__":
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    success = compile_po_files()
    sys.exit(0 if success else 1)