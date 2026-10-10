"""
Universal Environment & Port Bootstrap Helper for Bussiwzz.
Ensures seamless portability across all PCs, operating systems (Windows/Linux/macOS),
fresh git pulls, and network port configurations.
"""

from __future__ import annotations

import importlib.util
import os
import platform
import socket
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

PROJECT_DIR = Path(__file__).resolve().parent


def get_project_dir() -> Path:
    """Returns the absolute project root directory."""
    return PROJECT_DIR


def is_valid_python(executable: str | Path) -> bool:
    """Verifies that a python executable actually runs on *this* machine.
    
    Prevents errors when virtual environments are copied across different PCs.
    """
    exe_path = Path(executable)
    if not exe_path.is_file():
        return False
    try:
        proc = subprocess.run(
            [str(exe_path), "-c", "import sys; sys.exit(0)"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        return proc.returncode == 0
    except Exception:
        return False


def find_project_venv_python() -> Optional[Path]:
    """Finds a working virtual environment python executable in .venv or venv."""
    candidate_dirs = [PROJECT_DIR / ".venv", PROJECT_DIR / "venv"]
    for venv_dir in candidate_dirs:
        if not venv_dir.is_dir():
            continue
        if sys.platform == "win32":
            candidate = venv_dir / "Scripts" / "python.exe"
        else:
            candidate = venv_dir / "bin" / "python"

        if is_valid_python(candidate):
            return candidate
    return None


def has_module(module_name: str) -> bool:
    """Checks whether a Python module is importable in the current environment."""
    try:
        return importlib.util.find_spec(module_name) is not None
    except Exception:
        return False


def check_missing_modules(modules: List[str]) -> List[str]:
    """Returns a list of missing modules from the specified list."""
    missing = []
    for mod in modules:
        if not has_module(mod):
            missing.append(mod)
    return missing


def bootstrap_environment(required_modules: Optional[List[str]] = None) -> bool:
    """Ensures the process runs under a Python interpreter with required dependencies.

    If the current interpreter lacks required modules, this attempts to seamlessly
    re-execute under a local working virtual environment (.venv) if one exists on this PC.
    If no working virtual environment is found, it prints clear setup instructions.
    """
    if required_modules is None:
        required_modules = ["requests", "dotenv"]

    missing = check_missing_modules(required_modules)
    if not missing:
        return True

    # Current interpreter is missing modules. Check for a local working venv.
    venv_python = find_project_venv_python()
    if venv_python:
        current_exe = Path(sys.executable).resolve()
        target_exe = venv_python.resolve()
        if current_exe != target_exe:
            # Re-execute under the virtual environment interpreter
            try:
                if sys.argv and sys.argv[0] != "-c":
                    script_path = str(Path(sys.argv[0]).resolve()) if Path(sys.argv[0]).exists() else sys.argv[0]
                    args = [str(target_exe), script_path] + sys.argv[1:]
                    if sys.platform == "win32":
                        ret = subprocess.call(args)
                        sys.exit(ret)
                    else:
                        os.execv(str(target_exe), args)
            except Exception as exc:
                print(f"[Bussiwzz] Warning: Could not switch to virtual environment: {exc}")

    # No working venv or re-exec failed
    print("\n" + "=" * 70)
    print(" [Bussiwzz] Missing Dependencies Detected")
    print("=" * 70)
    print(f" Missing modules: {', '.join(missing)}")
    print("\n To automatically set up this computer:")
    print(f"     {sys.executable} run.py --setup")
    print("\n Or set up manually:")
    print("     python -m venv .venv")
    if sys.platform == "win32":
        print("     .venv\\Scripts\\activate")
    else:
        print("     source .venv/bin/activate")
    print("     pip install -r requirements.txt")
    print("\n Or run the standalone native desktop GUI (zero extra packages needed):")
    print("     python run.py --gui")
    if sys.platform == "win32":
        print("     (or double-click run_gui.bat)")
    else:
        print("     (or run sh run_gui.sh)")
    print("=" * 70 + "\n")
    sys.exit(1)


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Checks if a given network port is available for binding."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
    except OSError:
        return False


def find_available_port(start_port: int, max_attempts: int = 50, host: str = "127.0.0.1") -> int:
    """Finds the next free port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        if is_port_available(port, host):
            return port
    return start_port


def setup_virtualenv() -> int:
    """Creates a local virtual environment (.venv) on *this* PC and installs dependencies."""
    print("=" * 70)
    print(" [Bussiwzz] Setting up local environment for this computer...")
    print("=" * 70)
    venv_dir = PROJECT_DIR / ".venv"

    # 1. Create .venv
    print(f" Creating virtual environment at {venv_dir}...")
    try:
        proc = subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
    except subprocess.CalledProcessError as exc:
        print(f" Failed to create virtual environment: {exc}")
        return 1

    # 2. Locate pip
    if sys.platform == "win32":
        venv_py = venv_dir / "Scripts" / "python.exe"
    else:
        venv_py = venv_dir / "bin" / "python"

    if not is_valid_python(venv_py):
        print(f" Error: Virtual environment python at {venv_py} is not functional.")
        return 1

    # 3. Upgrade pip
    print(" Upgrading pip...")
    subprocess.run([str(venv_py), "-m", "pip", "install", "--upgrade", "pip", "--quiet"])

    # 4. Install requirements.txt
    req_file = PROJECT_DIR / "requirements.txt"
    if req_file.is_file():
        print(f" Installing dependencies from {req_file.name}...")
        res = subprocess.run([str(venv_py), "-m", "pip", "install", "-r", str(req_file)])
        if res.returncode != 0:
            print(" Pip install encountered an error. Check output above.")
            return res.returncode
    else:
        print(" Warning: requirements.txt not found.")

    # 5. Check .env
    env_file = PROJECT_DIR / ".env"
    env_example = PROJECT_DIR / ".env.example"
    if not env_file.is_file() and env_example.is_file():
        import shutil
        shutil.copyfile(env_example, env_file)
        print(" Created initial .env configuration from .env.example.")

    print("\n" + "=" * 70)
    print(" Setup completed successfully!")
    print(" To launch the desktop GUI:")
    print("     python run.py --gui")
    print(" To launch the web research dashboard:")
    print("     python run.py --web")
    print(" To launch the CLI research agent:")
    print("     python run.py --cli NVDA")
    print("=" * 70)
    return 0


def run_diagnostics() -> None:
    """Runs a complete system health check and prints diagnostic report."""
    print("\n" + "=" * 70)
    print(" BUSSIWZZ - SYSTEM PORTABILITY & ENVIRONMENT DIAGNOSTICS")
    print("=" * 70)

    # Operating System & Python
    print(f" Operating System   : {platform.system()} {platform.release()} ({platform.machine()})")
    print(f" Python Executable  : {sys.executable}")
    print(f" Python Version     : {platform.python_version()} ({'64-bit' if sys.maxsize > 2**32 else '32-bit'})")

    # Tkinter check
    try:
        import tkinter
        print(f" Tkinter (Native GUI): Available (Tcl/Tk version: {tkinter.Tcl().eval('info patchlevel')})")
    except ImportError:
        print(" Tkinter (Native GUI): NOT FOUND (install python3-tk or reinstall Python with Tcl/Tk)")

    # Virtual Environment
    active_venv = os.getenv("VIRTUAL_ENV")
    local_venv = find_project_venv_python()
    print(f" Active VirtualEnv  : {active_venv or 'None (using system Python)'}")
    print(f" Local Project venv : {local_venv or 'None (.venv not configured yet)'}")

    # Core Dependencies
    deps = [
        "flet",
        "requests",
        "httpx",
        "pydantic",
        "yfinance",
        "groq",
        "dotenv",
        "bs4",
        "mcp",
    ]
    print("\n Package Availability:")
    for dep in deps:
        installed = has_module(dep)
        status = "Installed" if installed else "MISSING"
        print(f"   - {dep:<18}: {status}")

    # Ports check
    web_port = int(os.getenv("PORT", "8550"))
    searx_url = os.getenv("SEARXNG_URL", "http://localhost:8888")
    print(f"\n Network Ports:")
    print(f"   - Web Dashboard Port {web_port} : {'Available' if is_port_available(web_port) else 'IN USE / OCCUPIED'}")
    print(f"   - SearXNG Endpoint URL  : {searx_url}")

    # .env File
    env_file = PROJECT_DIR / ".env"
    if env_file.is_file():
        has_key = False
        try:
            with open(env_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if line.strip().startswith("GROQ_API_KEY="):
                        val = line.strip().split("=", 1)[1].strip()
                        if val and val != "your_groq_api_key_here":
                            has_key = True
                            break
        except Exception:
            pass
        print(f"\n Configuration:")
        print(f"   - .env File             : Found ({env_file})")
        print(f"   - GROQ_API_KEY          : {'Configured' if has_key else 'Missing or placeholder (using mock/offline fallback)'}")
    else:
        print(f"\n Configuration:")
        print(f"   - .env File             : Not found (will use default mock/offline fallback)")

    print("=" * 70 + "\n")
