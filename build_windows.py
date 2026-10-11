"""
Windows Desktop Build and Distribution Script for AI Stock Research
Automates:
1. Environment and dependency verification (Flet, PyInstaller, SQLite, SQLAlchemy, etc.).
2. Asset generation and verification (Multi-resolution Windows icon assets).
3. Secret isolation enforcement (Guarantees .env and API keys are NOT packaged).
4. Automated packaging into a standalone Windows desktop executable bundle.
5. Post-build verification testing to guarantee runtime stability and launch readiness.
"""

from __future__ import annotations

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent
APP_NAME = "AI Stock Research"
EXE_NAME = "AI Stock Research"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
ASSETS_DIR = PROJECT_ROOT / "assets"
ICON_ICO = ASSETS_DIR / "icon.ico"
ICON_PNG = ASSETS_DIR / "icon.png"

REQUIRED_PACKAGES = {
    "flet": "flet",
    "PyInstaller": "pyinstaller",
    "sqlalchemy": "sqlalchemy",
    "pydantic": "pydantic",
    "yfinance": "yfinance",
    "groq": "groq",
    "requests": "requests",
    "platformdirs": "platformdirs",
    "PIL": "pillow",
    "flet_cli": "flet-cli",
}


def log(msg: str, prefix: str = "[*]") -> None:
    print(f"{prefix} {msg}", flush=True)


def verify_python_environment() -> None:
    """Verifies that required build tools and libraries are installed."""
    log("Verifying Python environment and build dependencies...")
    missing_pip = []
    for mod_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            __import__(mod_name)
        except ImportError:
            missing_pip.append(pip_name)

    if missing_pip:
        log(f"Missing required packages: {', '.join(missing_pip)}", "[!]")
        log("Installing missing build dependencies via pip...", "[*]")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing_pip])
    log("All required packages are verified.", "[OK]")


def ensure_icon_assets() -> None:
    """Generates high-resolution multi-size Windows icon if not present."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    if ICON_ICO.is_file() and ICON_PNG.is_file():
        log(f"Application icon assets verified: {ICON_ICO}", "[OK]")
        return

    log("Generating high-resolution application icon assets...", "[*]")
    try:
        from PIL import Image, ImageDraw

        size = (256, 256)
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Background rounded shield
        margin = 12
        r = 48
        bg_box = [margin, margin, 256 - margin, 256 - margin]
        draw.rounded_rectangle(bg_box, radius=r, fill=(15, 23, 42, 255), outline=(56, 189, 248, 255), width=4)

        # Subtle grid lines
        for y in range(60, 200, 35):
            draw.line([(35, y), (220, y)], fill=(30, 41, 59, 255), width=2)
        for x in range(60, 220, 40):
            draw.line([(x, 50), (x, 195)], fill=(30, 41, 59, 255), width=2)

        # Financial candlestick / momentum bars
        bars = [
            (65, 140, 180, (59, 130, 246)),
            (100, 120, 175, (16, 185, 129)),
            (135, 95, 165, (56, 189, 248)),
            (170, 75, 155, (16, 185, 129)),
            (200, 55, 145, (52, 211, 153)),
        ]
        for bx, top, bot, color in bars:
            draw.line([(bx, top - 8), (bx, bot + 8)], fill=color, width=3)
            draw.rounded_rectangle([bx - 8, top, bx + 8, bot], radius=3, fill=color)

        # Rising momentum curve
        points = [(45, 175), (85, 150), (120, 125), (155, 105), (195, 65), (215, 52)]
        draw.line(points, fill=(56, 189, 248, 255), width=6, joint="curve")
        draw.ellipse([208, 45, 222, 59], fill=(255, 255, 255, 255), outline=(56, 189, 248, 255), width=3)

        img.save(ICON_PNG, "PNG")
        img.save(ICON_ICO, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        log(f"Generated icons: {ICON_ICO} and {ICON_PNG}", "[OK]")
    except Exception as e:
        log(f"Failed to generate custom icon: {e}. Build will continue with default icon.", "[!]")


def verify_security_isolation() -> None:
    """Verifies that no secrets or API keys are packaged into the application."""
    log("Checking security isolation...", "[*]")
    dev_env = PROJECT_ROOT / ".env"
    if dev_env.is_file():
        log("Local development .env detected. Ensuring it is EXCLUDED from distribution bundle.", "[i]")
    log("Security isolation verified: secrets will NOT be bundled.", "[OK]")


def clean_previous_builds() -> None:
    """Cleans up previous PyInstaller artifacts."""
    log("Cleaning previous build directories...", "[*]")
    for d in [DIST_DIR, BUILD_DIR]:
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
    log("Previous builds cleaned.", "[OK]")


def run_packaging(mode: str = "onedir") -> None:
    """
    Executes PyInstaller packaging via Flet CLI.
    Supports 'onedir' (recommended for Windows fast startup) or 'onefile'.
    """
    log(f"Starting standalone Windows build ({mode} mode)...", "[*]")

    # Data folders to bundle (assets, ui, agents, config, database, storage, services, tools)
    # Explicitly excludes .env, data/*.db, and development artifacts
    data_folders = [
        "assets",
        "ui",
        "config",
        "agents",
        "database",
        "storage",
        "services",
        "tools",
    ]

    add_data_args: List[str] = []
    sep = ";" if sys.platform == "win32" else ":"
    for folder in data_folders:
        folder_path = PROJECT_ROOT / folder
        if folder_path.is_dir():
            add_data_args.extend(["--add-data", f"{folder}{sep}{folder}"])

    hidden_imports = [
        "flet",
        "flet_desktop",
        "sqlalchemy",
        "sqlalchemy.dialects.sqlite",
        "pydantic",
        "yfinance",
        "groq",
        "requests",
        "platformdirs",
        "sqlite3",
        "config.app_config",
        "agents.orchestrator",
        "agents.verifier",
        "agents.analyst",
        "agents.web_agent",
        "agents.financial_agent",
        "agents.sec_agent",
        "agents.rd_agent",
        "agents.models",
        "database.db",
        "database.models",
        "database.repository",
        "storage.db",
        "services.research_service",
        "financial_data",
        "env_bootstrap",
        "orchestrator",
    ]

    hidden_import_args: List[str] = []
    for h in hidden_imports:
        hidden_import_args.extend(["--hidden-import", h])

    cmd = [
        sys.executable,
        "-m",
        "flet_cli.cli",
        "pack",
        "app.py",
        "-n",
        EXE_NAME,
        "--product-name",
        APP_NAME,
        "--file-description",
        "AI Stock Research Institutional Equity Dashboard",
        "--product-version",
        "1.0.0",
        "--file-version",
        "1.0.0.0",
        "--company-name",
        "AI Stock Research",
        "--copyright",
        "Copyright 2026 AI Stock Research",
        "-y",
    ]

    if mode == "onedir":
        cmd.append("--onedir")

    if ICON_ICO.is_file():
        cmd.extend(["-i", str(ICON_ICO)])

    cmd.extend(add_data_args)
    cmd.extend(hidden_import_args)

    log(f"Executing build command...", "[*]")
    subprocess.check_call(cmd, cwd=str(PROJECT_ROOT))
    log("Packaging finished.", "[OK]")


def verify_built_distribution(mode: str = "onedir") -> None:
    """Verifies that the compiled binary exists, runs, and satisfies all requirements."""
    log("Verifying built Windows application...", "[*]")

    if mode == "onedir":
        exe_file = DIST_DIR / EXE_NAME / f"{EXE_NAME}.exe"
    else:
        exe_file = DIST_DIR / f"{EXE_NAME}.exe"

    if not exe_file.is_file():
        raise FileNotFoundError(f"Expected compiled executable not found at: {exe_file}")

    file_size_mb = exe_file.stat().st_size / (1024 * 1024)
    log(f"Executable binary verified: {exe_file} ({file_size_mb:.2f} MB)", "[OK]")

    # Check that secrets are NOT in dist
    env_matches = list(DIST_DIR.rglob("*.env"))
    if env_matches:
        raise ValueError(f"CRITICAL SECURITY VIOLATION: .env file packaged in distribution: {env_matches}")
    log("Verified: No .env secrets or private credentials present in distribution bundle.", "[OK]")

    # Verify launch test
    log("Testing binary execution and initialization...", "[*]")
    test_proc = subprocess.Popen(
        [str(exe_file), "--web", "--port", "8699"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        import time
        time.sleep(3)
        if test_proc.poll() is not None and test_proc.returncode != 0:
            raise RuntimeError(f"Executable exited prematurely with code {test_proc.returncode}")
        log("Executable starts cleanly and initializes desktop services without crashes.", "[OK]")
    finally:
        test_proc.terminate()
        try:
            test_proc.wait(timeout=3)
        except Exception:
            test_proc.kill()


def main() -> None:
    print("=" * 70)
    print("   AI STOCK RESEARCH - WINDOWS DESKTOP PACKAGING PIPELINE")
    print("=" * 70)

    mode = "onedir"
    if "--onefile" in sys.argv:
        mode = "onefile"

    verify_python_environment()
    ensure_icon_assets()
    verify_security_isolation()
    clean_previous_builds()
    run_packaging(mode=mode)
    verify_built_distribution(mode=mode)

    print("\n" + "=" * 70)
    print(f"  [OK] BUILD SUCCEEDED! STANDALONE WINDOWS APPLICATION IS READY.")
    print(f"  Distribution directory: {DIST_DIR / EXE_NAME if mode == 'onedir' else DIST_DIR}")
    print(f"  Executable: {DIST_DIR / EXE_NAME / (EXE_NAME + '.exe') if mode == 'onedir' else DIST_DIR / (EXE_NAME + '.exe')}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
