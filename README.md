# Bussiwzz - AI Stock Research & Equity Intelligence

Bussiwzz is an institutional-grade, cross-platform stock research agent and dashboard. It supports multiple presentation modes:
1. **Native Desktop Dashboard (Tkinter)**: Ultra-fast, institutional dark terminal aesthetics, 100% self-contained with **zero third-party dependencies** required.
2. **Modern Flet Research Dashboard**: Interactive multi-tab equity research application (desktop & web browser).
3. **Web Browser Interface**: Accessible across different devices on custom network ports.
4. **Command-Line Research Agent**: Fast terminal-driven research synthesis with live yfinance data, SEC EDGAR regulatory filings, and Groq LLM intelligence.

---

## Quick Start on Any PC (Windows, macOS, Linux)

Prerequisites: Python 3.10 or newer.

### 1. Standalone Native Desktop GUI (Zero Setup / Zero Dependencies)
Runs immediately without needing API keys or installing any pip packages:
- **Windows**: Double-click `run_gui.bat` (or run `python run.py --gui`)
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

- **No Machine-Specific Paths**: Virtual environments are local and ignored by Git. Launchers automatically detect and validate local Python interpreters without crashing on foreign paths.
- **Auto-Bootstrapping**: If you invoke `python app.py` or `python main.py` using your global Python interpreter, the application automatically locates the local `.venv` and runs seamlessly.
- **Port Conflict Handling**: The web server detects occupied network ports and automatically resolves to available open ports.
- **Encoding Resilient**: UTF-8 output streams are enforced across Windows, Linux, and macOS consoles.
