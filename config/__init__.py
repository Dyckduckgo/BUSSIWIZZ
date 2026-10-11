"""
Configuration package for AI Stock Research.
Manages user writable paths, secure API keys, and application preferences.
"""

from config.app_config import (
    get_app_dir,
    get_db_path,
    get_reports_dir,
    get_config_file,
    get_groq_api_key,
    load_app_config,
    save_app_config,
    ensure_writable_dirs,
    APP_NAME,
)

__all__ = [
    "get_app_dir",
    "get_db_path",
    "get_reports_dir",
    "get_config_file",
    "get_groq_api_key",
    "load_app_config",
    "save_app_config",
    "ensure_writable_dirs",
    "APP_NAME",
]
