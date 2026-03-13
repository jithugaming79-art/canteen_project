# 🍔 Campus Bites - Canteen Management System

## Quick Setup (Friend's Laptop)

### Prerequisites
1. **Python 3.10+** - Download from python.org
2. **MySQL Server** - Download from dev.mysql.com
3. **MySQL Workbench** - For importing database

### Step 1: Import Database
1. Open MySQL Workbench
2. Connect to localhost
3. Run: `CREATE DATABASE canteen_db;`
4. Go to Server → Data Import
5. Select `canteen_backup.sql` file
6. Click Start Import

### Step 2: Update Password
Open `canteen/settings.py` and change line 74:
```python
'PASSWORD': 'YOUR_MYSQL_PASSWORD',  # Change this!
```

### Step 3: Run Setup
Double-click `SETUP.bat` or run in command prompt:
```bash
pip install django mysqlclient django-allauth Pillow
python manage.py migrate
python manage.py runserver
```

### Step 4: Access Website
Open browser: http://localhost:8000

**Admin Login:** admin / admin123

---

## Features
- 📋 Menu with 56 items
- 🔍 Search & Filter (Veg/Non-Veg)
- 🛒 Cart & Checkout
- 💳 Online Payment (Simulated)
- 📦 Order Tracking
- 🚚 Delivery Options
- 👤 User Authentication
