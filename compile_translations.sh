#!/bin/bash

# Compile translation files
echo "Compiling translation files..."

# Create .mo files from .po files
python manage.py compilemessages -l en
python manage.py compilemessages -l cs

echo "Translation files compiled successfully!"