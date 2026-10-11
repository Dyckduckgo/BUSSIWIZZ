# AI Stock Research — Windows Desktop Distribution Guide

This document describes how to package, distribute, and run **AI Stock Research** as a standalone Windows desktop application without requiring Python, Antigravity, or terminal tools on the end-user machine.

---

## 1. Quick Build Command

To compile the standalone Windows application bundle:

### Option A: Using the Automated Build Script (Recommended)
```cmd
python build_windows.py
```
Or double-click:
```cmd
build_windows.bat
```

### Option B: Using the Flet CLI Directly
```cmd
flet pack app.py --onedir -n "AI Stock Research" -i "assets/icon.ico" --product-name "AI Stock Research" --file-description "AI Stock Research Institutional Equity Dashboard" --product-version "1.0.0" --company-name "AI Stock Research" --copyright "Copyright 2026 AI Stock Research" --add-data "assets;assets" --add-data "ui;ui" --add-data "config;config" --add-data "agents;agents" --add-data "database;database" --add-data "storage;storage" --add-data "services;services" --add-data "tools;tools" --hidden-import flet --hidden-import flet_desktop --hidden-import sqlalchemy --hidden-import sqlalchemy.dialects.sqlite --hidden-import pydantic --hidden-import yfinance --hidden-import groq --hidden-import requests --hidden-import platformdirs --hidden-import sqlite3 -y
```

### Option C: Using PyInstaller with the Included Spec File
```cmd
pyinstaller AIStockResearch.spec --noconfirm
```

---

## 2. Output and Distribution Structure

The build process outputs a complete standalone Windows application folder at:
```
dist/
└── AI Stock Research/
    ├── AI Stock Research.exe    <-- Main desktop application executable
    └── _internal/                <-- Python runtime, DLLs, Flutter engine, assets
```

To distribute to end users:
1. Zip the `dist/AI Stock Research` folder.
2. The user unzips the folder and double-clicks `AI Stock Research.exe`.
3. No Python installation, IDE, or terminal is required.

---

## 3. Key Distribution Requirements & Architecture

### A. Secret and API Key Isolation (Zero Credentials Packaged)
* **Never Bundled**: `.env` and hardcoded API keys are strictly excluded from the PyInstaller build bundle and git repository.
* **Resolution Order**:
  1. `GROQ_API_KEY` system environment variable.
  2. Secure user configuration in `%APPDATA%\AIStockResearch\config.json`.
  3. Local `.env` in current directory (developer mode only).
* **In-App Configuration**: Users can enter and update their Groq API Key directly in the application via **Settings** (Sidebar gear icon). It is stored securely in the user's AppData directory and never modifies the application binary.

### B. User-Writable Application Data & SQLite Database
Standalone applications installed in `Program Files` cannot write to their installation directory without administrator privileges. AI Stock Research dynamically resolves standard writable paths:

| Data Type | Persistent Location | Environment Override |
|---|---|---|
| **Application Data** | `%APPDATA%\AIStockResearch` | `AI_STOCK_RESEARCH_DIR` |
| **SQLite Database** | `%APPDATA%\AIStockResearch\data\stock_research.db` | `STOCK_RESEARCH_DB_PATH` |
| **Exported Reports** | `%APPDATA%\AIStockResearch\reports\` | `STOCK_RESEARCH_REPORTS_DIR` |
| **User Settings** | `%APPDATA%\AIStockResearch\config.json` | N/A |

### C. Assets and Application Icon
* High-resolution application icons are embedded in the executable (`assets/icon.ico`) and displayed on the desktop taskbar/window (`assets/icon.png`).
* The application name in metadata, task manager, and window title is set to: **AI Stock Research**.

### D. Zero Antigravity Dependency
* The application runs completely decoupled from Google Antigravity or any development IDE.
* All agent orchestration, verification, scoring, and UI execution are self-contained using standard open-source Python packages.

---

## 4. Verification and Testing

To test the compiled executable before distribution:

```cmd
python -c "import subprocess, time; p = subprocess.Popen([r'dist\AI Stock Research\AI Stock Research.exe', '--web', '--port', '8699']); time.sleep(3); assert p.poll() is None, 'Failed'; p.terminate(); print('Binary test PASSED!')"
```
Or launch `dist\AI Stock Research\AI Stock Research.exe` directly on any 64-bit Windows machine.
