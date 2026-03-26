#!/bin/bash

# Compile translation files
echo "Compiling translation files..."

# Create .mo files from .po files
python3 manage.py compilemessages -l en
python3 manage.py compilemessages -l cs

echo "Translation files compiled successfully!"