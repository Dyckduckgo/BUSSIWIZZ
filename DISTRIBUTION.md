# BussWizz (AI Stock Research) — Windows Desktop Distribution Guide

This document describes how to package, distribute, and run **BussWizz** (packaged as **AI Stock Research**) as a standalone Windows desktop application without requiring Python, Antigravity, or terminal tools on the end-user machine.

---

## 1. Quick Build Command

To compile the standalone Windows application bundle and generate the release ZIP archive:

### Option A: Using the Automated Build Script (Recommended)
```cmd
python build_windows.py
```
Or double-click:
```cmd
build_windows.bat
```
*The build script automatically runs the PyInstaller/Flet build, verifies startup stability, packs the entire distribution into a versioned `.zip` archive, and computes the cryptographic SHA-256 checksum.*

### Option B: Using PyInstaller with the Included Spec File
```cmd
pyinstaller AIStockResearch.spec --noconfirm
```

---

## 2. Output and Distribution Structure

The build pipeline outputs to `dist/`:
```
dist/
├── AI Stock Research/
│   ├── AI Stock Research.exe                 <-- Main desktop application executable
│   └── _internal/                             <-- Embedded Python runtime, Flutter engine, assets
├── AI_Stock_Research_v1.0.0_Windows_x64.zip    <-- Complete portable release archive
└── AI_Stock_Research_v1.0.0_Windows_x64.zip.sha256 <-- Verification checksum
```

### To Distribute on GitHub Releases:
1. Tag your release on GitHub (e.g. `v1.0.0`).
2. Attach `dist/AI_Stock_Research_v1.0.0_Windows_x64.zip` and `dist/AI_Stock_Research_v1.0.0_Windows_x64.zip.sha256` to the release.
3. End users download and unzip `AI_Stock_Research_v1.0.0_Windows_x64.zip`, then double-click `AI Stock Research.exe`.
4. No Python installation, IDE, or terminal is required.

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

### Verifying Release Checksums:
End users can verify the integrity of the downloaded archive in Windows PowerShell:
```powershell
Get-FileHash .\AI_Stock_Research_v1.0.0_Windows_x64.zip -Algorithm SHA256
```
Compare the output string against the contents of `AI_Stock_Research_v1.0.0_Windows_x64.zip.sha256`.
