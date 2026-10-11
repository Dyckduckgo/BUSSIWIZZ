"""
Settings Modal Component
Configuration dialog for local-first architecture endpoints, LLM model choice,
secure API keys, and persistent user AppData storage paths.
"""

import os
from typing import Callable, Optional
import flet as ft
from ui.theme import (
    BG_SURFACE,
    BORDER_COLOR,
    PRIMARY,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
)
from config.app_config import (
    get_groq_api_key,
    get_db_path,
    get_reports_dir,
    save_app_config,
    load_app_config,
)


def create_settings_dialog(page: ft.Page, on_save: Optional[Callable[[], None]] = None) -> ft.AlertDialog:
    """Constructs a modal dialog for configuring application preferences."""
    user_cfg = load_app_config()

    current_key = get_groq_api_key() or ""
    current_searxng = user_cfg.get("searxng_url") or os.getenv("SEARXNG_URL", "http://localhost:8888")
    current_model = user_cfg.get("default_model") or os.getenv("DEFAULT_MODEL", "llama-3.3-70b-versatile")
    current_depth = user_cfg.get("research_depth", "deep")

    groq_key_input = ft.TextField(
        label="Groq API Key (Free tier supported)",
        value=current_key,
        hint_text="gsk_... (stored securely in user AppData)",
        password=True,
        can_reveal_password=True,
        prefix_icon=ft.Icons.KEY_OUTLINED,
        text_size=13,
        helper_text="Read from environment or saved in %APPDATA%\\AIStockResearch\\config.json",
    )

    searxng_url_input = ft.TextField(
        label="SearXNG MCP Endpoint",
        value=current_searxng,
        hint_text="http://localhost:8888",
        prefix_icon=ft.Icons.TRAVEL_EXPLORE,
        text_size=13,
    )

    model_dropdown = ft.Dropdown(
        label="Groq Reasoning Model",
        value=current_model,
        options=[
            ft.dropdown.Option("llama-3.3-70b-versatile", "Llama 3.3 70B Versatile (Recommended)"),
            ft.dropdown.Option("llama-3.1-8b-instant", "Llama 3.1 8B Instant (Fast)"),
            ft.dropdown.Option("mixtral-8x7b-32768", "Mixtral 8x7B (Long Context)"),
        ],
        text_size=13,
    )

    db_path_input = ft.TextField(
        label="Local SQLite Database Storage (User-Writable)",
        value=str(get_db_path()),
        prefix_icon=ft.Icons.STORAGE,
        text_size=12,
        read_only=True,
    )

    reports_path_input = ft.TextField(
        label="Reports Output Directory (User-Writable)",
        value=str(get_reports_dir()),
        prefix_icon=ft.Icons.FOLDER_OUTLINED,
        text_size=12,
        read_only=True,
    )

    depth_radio = ft.RadioGroup(
        content=ft.Row([
            ft.Radio(value="standard", label="Standard (Fast)"),
            ft.Radio(value="deep", label="Deep Comprehensive (Full Citations)"),
        ], spacing=16),
        value=current_depth,
    )

    def close_and_save(e):
        save_app_config(
            groq_api_key=groq_key_input.value.strip(),
            searxng_url=searxng_url_input.value.strip(),
            default_model=model_dropdown.value,
            research_depth=depth_radio.value,
        )
        page.pop_dialog()
        page.update()
        if on_save:
            on_save()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon(ft.Icons.SETTINGS_OUTLINED, color=PRIMARY, size=22),
            ft.Text("Application Settings & Architecture", size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
        ], spacing=8),
        content=ft.Container(
            content=ft.Column([
                ft.Text("API CREDENTIALS & REASONING (SECURE / UNBUNDLED)", size=11, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                groq_key_input,
                model_dropdown,
                searxng_url_input,
                ft.Divider(color=BORDER_COLOR, height=16),
                ft.Text("PERSISTENT STORAGE & REPORTS", size=11, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                db_path_input,
                reports_path_input,
                ft.Divider(color=BORDER_COLOR, height=16),
                ft.Text("RESEARCH RIGOR & DEPTH", size=11, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                depth_radio,
            ], spacing=10, scroll=ft.ScrollMode.AUTO),
            width=540,
            height=460,
            padding=10,
        ),
        actions=[
            ft.OutlinedButton("Cancel", on_click=lambda e: (page.pop_dialog(), page.update())),
            ft.FilledButton(
                "Save Preferences",
                style=ft.ButtonStyle(bgcolor=PRIMARY),
                on_click=close_and_save,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=BG_SURFACE,
        shape=ft.RoundedRectangleBorder(radius=12),
    )

    return dialog
