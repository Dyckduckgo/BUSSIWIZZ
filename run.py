"""
Universal Cross-Platform Launcher for Bussiwzz.
Works seamlessly across all PCs (Windows, macOS, Linux), fresh git pulls, and network ports.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
os.chdir(PROJECT_DIR)

from env_bootstrap import (
    find_available_port,
    has_module,
    is_valid_python,
    run_diagnostics,
    setup_virtualenv,
)


def launch_native_gui() -> int:
    """Launches the Tkinter native desktop dashboard (requires 0 third-party packages)."""
    if sys.version_info < (3, 10):
        print("Python 3.10 or newer is required. Found:", sys.version.split()[0])
        return 1

    try:
        import tkinter  # noqa: F401
    except ImportError:
        print("\n" + "=" * 70)
        print(" [Bussiwzz] Tkinter is not installed on this Python installation.")
        print("=" * 70)
        if sys.platform == "darwin":
            print(" On macOS: Install with Homebrew (`brew install python-tk`) or")
            print(" download Python with Tcl/Tk from https://www.python.org/downloads/")
        elif sys.platform.startswith("linux"):
            print(" On Debian/Ubuntu : sudo apt update && sudo apt install -y python3-tk")
            print(" On Fedora/RHEL   : sudo dnf install -y python3-tkinter")
            print(" On Arch Linux    : sudo pacman -S --noconfirm tk")
        else:
            print(" On Windows: Reinstall Python from https://www.python.org/downloads/")
            print(" and ensure 'tcl/tk and IDLE' checkbox is checked.")
        print("\n Alternatively, run the web dashboard or CLI:")
        print("     python run.py --web")
        print("     python run.py --cli NVDA")
        print("=" * 70 + "\n")
        return 1

    try:
        from gui import launch_gui
    except Exception as exc:
        print(f"Could not start Bussiwzz GUI: {exc}")
        return 1

    launch_gui()
    return 0


def launch_flet_app(web: bool = False, host: str | None = None, port: int | None = None) -> int:
    """Launches the Flet equity research dashboard."""
    from env_bootstrap import bootstrap_environment
    bootstrap_environment(["flet"])
    from app import launch_app
    launch_app(host=host, port=port, web=web)
    return 0


def launch_cli_agent(ticker: str | None = None) -> int:
    """Launches the CLI research agent."""
    from env_bootstrap import bootstrap_environment
    bootstrap_environment(["requests", "dotenv", "groq"])
    import main as cli_main
    if ticker:
        import asyncio
        asyncio.run(cli_main.run_research_flow(ticker))
    else:
        cli_main.interactive_loop()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bussiwzz - AI Stock Research Agent & Dashboard Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py              # Launch native desktop GUI (or web UI if headless)
  python run.py --gui        # Launch native desktop Tkinter GUI (zero dependencies)
  python run.py --app        # Launch modern Flet desktop dashboard
  python run.py --web        # Launch web dashboard in browser (default port 8550)
  python run.py --web --port 8080 # Launch web dashboard on port 8080
  python run.py --cli NVDA   # Run CLI research agent for NVIDIA
  python run.py --setup      # Automatically set up .venv and install requirements
  python run.py --check      # Run system diagnostics and verify environment
        """,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--gui", action="store_true", help="Launch native Tkinter desktop dashboard (zero dependencies)")
    group.add_argument("--app", action="store_true", help="Launch Flet equity research desktop application")
    group.add_argument("--web", action="store_true", help="Launch research dashboard in web browser")
    group.add_argument("--cli", nargs="?", const="", default=None, metavar="TICKER", help="Launch CLI agent (optionally specify ticker)")
    group.add_argument("--setup", action="store_true", help="Set up virtual environment (.venv) and install dependencies")
    group.add_argument("--check", action="store_true", help="Run environment and port diagnostics")

    parser.add_argument("--port", type=int, default=None, help="Port for web mode (default: 8550 or $PORT)")
    parser.add_argument("--host", type=str, default=None, help="Host for web mode (default: 127.0.0.1 or 0.0.0.0)")

    args = parser.parse_args()

    if args.check:
        run_diagnostics()
        return 0

    if args.setup:
        return setup_virtualenv()

    if args.gui:
        return launch_native_gui()

    if args.app:
        return launch_flet_app(web=False)

    if args.web:
        return launch_flet_app(web=True, host=args.host, port=args.port)

    if args.cli is not None:
        return launch_cli_agent(ticker=args.cli if args.cli else None)

    # Default action (no flag specified):
    # If a display is available, start native GUI.
    # If headless (e.g. cloud VM, remote Linux server, container without DISPLAY), launch web mode.
    is_headless = sys.platform != "win32" and not (os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))
    if is_headless:
        print("[Bussiwzz] No graphical display detected. Starting in Web Browser mode...")
        return launch_flet_app(web=True, host=args.host, port=args.port)
    else:
        return launch_native_gui()


if __name__ == "__main__":
    raise SystemExit(main())
