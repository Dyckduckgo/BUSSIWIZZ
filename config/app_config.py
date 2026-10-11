"""
Application Configuration and Storage Management for AI Stock Research
Provides:
- User-writable AppData directories for SQLite databases and report files.
- Secure, unbundled API key storage and resolution (Env Vars -> AppData config -> dev .env).
- Dynamic asset path discovery supporting both dev mode and PyInstaller frozen binaries.
- Safe cross-platform fallback mechanisms for Windows, macOS, and Linux.
"""

from __future__ import annotations

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("config.app")

APP_NAME = "AI Stock Research"
APP_DIR_NAME = "AIStockResearch"


def is_frozen() -> bool:
    """Returns True if running inside a PyInstaller frozen bundle."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_bundle_dir() -> Path:
    """Returns the bundle root directory (either _MEIPASS or repository root)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


def get_assets_dir() -> Path:
    """
    Returns the resolved assets directory containing icons, themes, and static files.
    Works seamlessly in dev mode and within PyInstaller onefile/onedir distributions.
    """
    # Check next to executable first (for onedir distributions)
    if is_frozen():
        exe_dir = Path(sys.executable).resolve().parent
        candidate = exe_dir / "assets"
        if candidate.is_dir():
            return candidate

    # Check inside _MEIPASS (for onefile distributions) or repository root
    bundle_assets = get_bundle_dir() / "assets"
    if bundle_assets.is_dir():
        return bundle_assets

    # Fallback to repository root / assets
    repo_assets = Path(__file__).resolve().parent.parent / "assets"
    repo_assets.mkdir(parents=True, exist_ok=True)
    return repo_assets


def get_app_dir() -> Path:
    """
    Returns the user-writable application data directory:
    - Windows: %APPDATA%\\AIStockResearch (e.g. C:\\Users\\<User>\\AppData\\Roaming\\AIStockResearch)
    - macOS: ~/Library/Application Support/AIStockResearch
    - Linux: ~/.local/share/AIStockResearch
    Can be overridden via AI_STOCK_RESEARCH_DIR environment variable.
    """
    env_override = os.getenv("AI_STOCK_RESEARCH_DIR") or os.getenv("STOCK_RESEARCH_DATA_DIR")
    if env_override:
        p = Path(env_override)
        p.mkdir(parents=True, exist_ok=True)
        return p

    try:
        import platformdirs
        p = Path(platformdirs.user_data_dir(APP_DIR_NAME, appauthor=APP_DIR_NAME))
    except Exception:
        if sys.platform == "win32":
            base = os.getenv("APPDATA") or os.path.expanduser("~\\AppData\\Roaming")
            p = Path(base) / APP_DIR_NAME
        elif sys.platform == "darwin":
            p = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
        else:
            p = Path.home() / ".local" / "share" / APP_DIR_NAME

    p.mkdir(parents=True, exist_ok=True)
    return p


def get_db_path() -> Path:
    """
    Returns the persistent SQLite database path in user-writable application data storage.
    Can be overridden via STOCK_RESEARCH_DB_PATH or DATABASE_PATH environment variables.
    """
    env_db = os.getenv("STOCK_RESEARCH_DB_PATH") or os.getenv("DATABASE_PATH")
    if env_db:
        p = Path(env_db)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    data_dir = get_app_dir() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "stock_research.db"


def get_reports_dir() -> Path:
    """
    Returns the user-writable directory for saving generated research reports and dossiers.
    Can be overridden via STOCK_RESEARCH_REPORTS_DIR environment variable.
    """
    env_rep = os.getenv("STOCK_RESEARCH_REPORTS_DIR")
    if env_rep:
        p = Path(env_rep)
    else:
        p = get_app_dir() / "reports"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_config_file() -> Path:
    """Returns the persistent JSON configuration file path in user AppData."""
    return get_app_dir() / "config.json"


def ensure_writable_dirs() -> None:
    """Ensures all writable directories exist on startup."""
    get_app_dir()
    get_db_path().parent.mkdir(parents=True, exist_ok=True)
    get_reports_dir().mkdir(parents=True, exist_ok=True)


def load_app_config() -> Dict[str, Any]:
    """Loads application preferences from user AppData config.json."""
    cfg_file = get_config_file()
    if cfg_file.is_file():
        try:
            return json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Failed to read user config file {cfg_file}: {e}")
    return {}


def save_app_config(
    groq_api_key: Optional[str] = None,
    searxng_url: Optional[str] = None,
    default_model: Optional[str] = None,
    research_depth: Optional[str] = None,
    custom_settings: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Saves user configuration safely to user AppData without touching project code.
    Also synchronizes environment variables for the running process.
    """
    cfg = load_app_config()

    if groq_api_key is not None:
        cfg["groq_api_key"] = groq_api_key.strip()
        os.environ["GROQ_API_KEY"] = groq_api_key.strip()

    if searxng_url is not None:
        cfg["searxng_url"] = searxng_url.strip()
        os.environ["SEARXNG_URL"] = searxng_url.strip()

    if default_model is not None:
        cfg["default_model"] = default_model.strip()
        os.environ["DEFAULT_MODEL"] = default_model.strip()

    if research_depth is not None:
        cfg["research_depth"] = research_depth.strip()

    if custom_settings:
        cfg.update(custom_settings)

    cfg_file = get_config_file()
    try:
        cfg_file.parent.mkdir(parents=True, exist_ok=True)
        cfg_file.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        logger.info(f"Updated user configuration in {cfg_file}")
    except Exception as e:
        logger.error(f"Failed to write user config to {cfg_file}: {e}")


def get_groq_api_key() -> Optional[str]:
    """
    Resolves the Groq API key securely with clear priority:
    1. Environment variable GROQ_API_KEY
    2. Secure user config in AppData config.json
    3. Local .env file (if running unbundled in local development)
    Returns None if no key is found. Never hardcodes or bundles secrets.
    """
    # 1. Environment variable
    env_key = os.getenv("GROQ_API_KEY")
    if env_key and env_key.strip() and not env_key.startswith("your_"):
        return env_key.strip()

    # 2. User AppData configuration
    user_cfg = load_app_config()
    cfg_key = user_cfg.get("groq_api_key")
    if cfg_key and cfg_key.strip() and not cfg_key.startswith("your_"):
        os.environ["GROQ_API_KEY"] = cfg_key.strip()
        return cfg_key.strip()

    # 3. Dev .env file (only if not frozen in a standalone binary)
    if not is_frozen():
        try:
            from dotenv import load_dotenv
            dev_env = Path(__file__).resolve().parent.parent / ".env"
            if dev_env.is_file():
                load_dotenv(dev_env)
                re_check = os.getenv("GROQ_API_KEY")
                if re_check and re_check.strip() and not re_check.startswith("your_"):
                    return re_check.strip()
        except Exception:
            pass

    return None
