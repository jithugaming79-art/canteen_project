@echo off
echo ==========================================
echo   Campus Bites - Canteen Management System
echo   Setup Script
echo ==========================================
echo.

echo [1/4] Installing Python dependencies...
pip install django mysqlclient django-allauth Pillow requests
echo.

echo [2/4] running database migrations...
echo.

echo [3/4] Running database migrations...
python manage.py migrate
echo.

echo [4/4] Starting server...
echo.

echo ==========================================
echo   Setup Complete!
echo ==========================================
echo.
echo Admin Login: admin / admin123
echo.
echo Starting server...
python manage.py runserver

pause
