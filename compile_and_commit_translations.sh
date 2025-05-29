#!/bin/bash
# Script to compile translations and prepare for commit

echo "Compiling Django translations..."
python manage.py compilemessages

if [ $? -eq 0 ]; then
    echo "✅ Translations compiled successfully!"
    echo ""
    echo "Files to commit:"
    git status locale/
    echo ""
    echo "Ready to commit both .po and .mo files"
else
    echo "❌ Error compiling translations!"
    exit 1
fi