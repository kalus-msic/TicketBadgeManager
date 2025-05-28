#!/bin/bash

# Setup script for macOS/Linux development

echo "Setting up development environment..."

# Create virtual environment with Python 3.11
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements without Windows-specific packages
pip install Django==5.1.1
pip install pillow==10.4.0
pip install pandas==2.2.3
pip install numpy==2.1.1
pip install django-sslserver==0.22
pip install requests==2.32.3
pip install python-dotenv==1.0.0
pip install django-ratelimit==4.1.0
pip install qrcode==7.4.2
pip install django-crispy-forms==2.1
pip install crispy-bootstrap5==2024.2

# Create .env file from example
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file. Please update it with your settings."
fi

# Create logs directory
mkdir -p logs

# Run migrations
python manage.py migrate

# Create superuser prompt
echo ""
echo "Setup complete! To create a superuser account, run:"
echo "python manage.py createsuperuser"
echo ""
echo "To start the development server, run:"
echo "python manage.py runsslserver"