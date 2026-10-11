# BussWizz - AI Stock Research & Institutional Equity Intelligence

**BussWizz** (packaged as **AI Stock Research**) is an institutional-grade stock research agent and analytical dashboard. It combines live market data from Yahoo Finance, regulatory filings from SEC EDGAR, academic R&D papers, and Groq LLM synthesis with multi-agent factual verification.

---

## 🚀 Download Pre-Built Windows Application (No Python Required)

For end users on Windows 10 or 11 (64-bit):

1. **Download**: Get the latest `AI_Stock_Research_v1.0.0_Windows_x64.zip` from the [GitHub Releases](https://github.com/Dyckduckgo/BUSSIWIZZ/releases) page.
2. **Extract**: Unzip the folder anywhere on your computer (e.g. `Desktop` or `Documents`).
3. **Launch**: Open the extracted folder and double-click:
   ```
   AI Stock Research.exe
   ```
   *No installation, Python runtime, or command-line setup is needed.*

### First-Run & API Key Setup
- The application launches in dark institutional mode ready to analyze stocks.
- **Configuring Groq API Key (Recommended)**:
  1. Click the **Settings** gear icon in the lower-left sidebar.
  2. Paste your free Groq API key from [https://console.groq.com/keys](https://console.groq.com/keys).
  3. Click **Save Preferences**.
  *Your API key is securely saved to your local Windows profile (`%APPDATA%\AIStockResearch\config.json`) and is never embedded in the app files.*
- **Offline / Zero-Key Mode**: If no API key is configured, the agent seamlessly uses deterministic local factual synthesis without crashing.

---

## 🛠️ Running from Source (Developers & Cross-Platform)

Prerequisites: Python 3.10 to 3.14 on Windows, macOS, or Linux.

### Standalone Native GUI (Zero Dependencies)
Runs immediately without installing any third-party pip packages:
- **Windows**: Double-click `run_gui.bat` (or `python run.py --gui`)
- **macOS / Linux**: Run `sh run_gui.sh` (or `python3 run.py --gui`)

*Linux Note: If Tkinter is not pre-installed on your distribution, install it via:*
```sh
# Debian / Ubuntu
sudo apt install -y python3-tk

# Fedora / RHEL
sudo dnf install -y python3-tkinter

# Arch Linux
sudo pacman -S tk
```

---

## Live Research & Web Dashboard

To enable live financial metrics, SEC EDGAR filing parsers, and web research, initialize the local environment:

### One-Command Setup (Recommended)
From the project folder, run:
```sh
python run.py --setup
```
This automatically creates a clean `.venv` for your specific operating system, upgrades pip, and installs all required dependencies.

### Manual Setup
```sh
# 1. Create a clean virtual environment
python -m venv .venv

# 2. Activate it
# Windows (PowerShell/CMD):
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Configure API Keys (Optional)
Copy `.env.example` to `.env`:
```sh
cp .env.example .env
```
Add your free Groq API key from [https://console.groq.com/keys](https://console.groq.com/keys). If omitted, the agent seamlessly operates in offline / mock fallback mode without crashing.

---

## Running Modes & Port Configuration

### Web Browser Mode (Custom Ports & Remote Access)
Run the web application and access it from any browser:
```sh
# Run on default port 8550
python run.py --web

# Run on custom port (e.g., 8080)
python run.py --web --port 8080

# Bind to all network interfaces (for local network or container access)
python run.py --web --host 0.0.0.0 --port 8080
```
On Windows, you can also launch `run_web.bat [port]`.
On macOS/Linux, run `sh run_web.sh [port]`.

### Modern Desktop App
```sh
python run.py --app
# Or: python app.py
```

### Command-Line Research Agent
```sh
# Interactive prompt
python run.py --cli

# Direct ticker research (e.g. NVIDIA)
python run.py --cli NVDA
```

### System Diagnostics
To inspect Python versions, Tkinter support, package installations, and port availability on any machine:
```sh
python run.py --check
```

---

## Cross-PC Portability & Git Pulls

- **Encoding Resilient**: UTF-8 output streams are enforced across Windows, Linux, and macOS consoles.

---

## 📦 Building Standalone Windows Releases

To compile the application into a standalone Windows desktop executable and release ZIP:
```cmd
build_windows.bat
# Or: python build_windows.py
```
This automatically produces:
1. `dist\AI Stock Research\` — Standalone desktop application folder.
2. `dist\AI_Stock_Research_v1.0.0_Windows_x64.zip` — Portable release archive for distribution.
3. `dist\AI_Stock_Research_v1.0.0_Windows_x64.zip.sha256` — Cryptographic checksum for release verification.

See [DISTRIBUTION.md](DISTRIBUTION.md) for complete packaging, security isolation, and GitHub release deployment documentation.
