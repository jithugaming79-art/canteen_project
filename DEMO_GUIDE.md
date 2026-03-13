# 🚀 CampusBites - Demo Setup Guide

## What Your Friend's Laptop Needs (Prerequisites)

| Software | Version | Download Link |
|----------|---------|---------------|
| **Python** | 3.10+ | [python.org/downloads](https://www.python.org/downloads/) |
| **MySQL** | 8.0+ | [dev.mysql.com/downloads](https://dev.mysql.com/downloads/installer/) |

> **IMPORTANT**: During Python install, check ✅ "Add Python to PATH"  
> During MySQL install, remember the **root password** — you'll need it.

---

## Option A: One-Click Setup (Easiest)

1. Copy the **entire `canteen_project` folder** to a USB drive
2. On friend's laptop, paste the folder anywhere (e.g., Desktop)
3. Double-click **`SETUP_DEMO.bat`**
4. Enter the MySQL root password when asked
5. Open browser → `http://127.0.0.1:8000/home/`

---

## Option B: Manual Step-by-Step

### Step 1: Copy Project
Copy the **entire `canteen_project` folder** via USB drive or cloud.

### Step 2: Open Terminal
Open Command Prompt or PowerShell in the `canteen_project` folder.

### Step 3: Create Virtual Environment
```bash
python -m venv venv
```

### Step 4: Install Dependencies
```bash
venv\Scripts\pip.exe install -r requirements.txt
```

### Step 5: Setup MySQL Database
Open MySQL command line and run:
```sql
CREATE DATABASE canteen_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Then import the data:
```bash
mysql -u root -p canteen_db < db_backup.sql
```

### Step 6: Update .env File
Edit `.env` and change `DB_PASSWORD` to the friend's MySQL root password:
```
DB_PASSWORD=<friend's_mysql_password>
```

### Step 7: Run the Server
```bash
venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

### Step 8: Open in Browser
- **Home**: http://127.0.0.1:8000/home/
- **Admin**: http://127.0.0.1:8000/admin/
- **Kitchen**: http://127.0.0.1:8000/kitchen/dashboard/

---

## Login Credentials

| Role | Username | Password |
|------|----------|----------|
| **Admin/Superuser** | *(your admin username)* | *(your admin password)* |
| **Kitchen Staff** | *(kitchen username)* | *(kitchen password)* |
| **Customer** | *(any registered user)* | *(their password)* |

> ⚠️ Fill in your actual usernames/passwords above before the demo!

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `python not found` | Install Python and check "Add to PATH" |
| `mysql not found` | Add MySQL `bin` folder to system PATH |
| `Access denied for user 'root'` | Check MySQL password in `.env` file |
| `ModuleNotFoundError` | Run `venv\Scripts\pip.exe install -r requirements.txt` |
| `Database not found` | Run `mysql -u root -p -e "CREATE DATABASE canteen_db;"` |

---

## Files You Need to Copy

```
canteen_project/          ← Copy this ENTIRE folder
├── db_backup.sql         ← Database with all your data
├── requirements.txt      ← Python packages list
├── SETUP_DEMO.bat        ← One-click setup script
├── .env                  ← Config (update password!)
├── manage.py
├── venv/                 ← Virtual environment (can recreate)
├── media/                ← Food images
├── static/               ← CSS, JS, icons
├── templates/            ← HTML templates
└── ... (all other folders)
```

> 💡 **Tip**: You CAN skip copying the `venv/` folder (saves ~200MB). 
> The setup script will recreate it automatically.
