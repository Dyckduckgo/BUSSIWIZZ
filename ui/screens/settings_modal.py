"""
Settings Modal Component
Configuration dialog for local-first architecture endpoints, LLM model choice, and app preferences.
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


def create_settings_dialog(page: ft.Page, on_save: Optional[Callable[[], None]] = None) -> ft.AlertDialog:
    """Constructs a modal dialog for configuring application preferences."""

    default_searxng = os.getenv("SEARXNG_URL", "http://localhost:8888")
    searxng_url_input = ft.TextField(
        label="SearXNG MCP Endpoint",
        value=default_searxng,
        hint_text=default_searxng,
        prefix_icon=ft.Icons.TRAVEL_EXPLORE,
        text_size=13,
    )

    model_dropdown = ft.Dropdown(
        label="Groq Reasoning Model",
        value="llama-3.3-70b-versatile",
        options=[
            ft.dropdown.Option("llama-3.3-70b-versatile", "Llama 3.3 70B Versatile (Recommended)"),
            ft.dropdown.Option("llama-3.1-8b-instant", "Llama 3.1 8B Instant (Fast)"),
            ft.dropdown.Option("mixtral-8x7b-32768", "Mixtral 8x7B (Long Context)"),
        ],
        text_size=13,
    )

    db_path_input = ft.TextField(
        label="Local SQLite Database Path",
        value="data/stock_research.db",
        hint_text="data/stock_research.db",
        prefix_icon=ft.Icons.STORAGE,
        text_size=13,
        read_only=True,
    )

    depth_radio = ft.RadioGroup(
        content=ft.Row([
            ft.Radio(value="standard", label="Standard (Fast)"),
            ft.Radio(value="deep", label="Deep Comprehensive (Full Citations)"),
        ], spacing=16),
        value="deep",
    )

    def close_dialog(e):
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
                ft.Text("LOCAL-FIRST BACKEND SERVICES", size=11, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                searxng_url_input,
                model_dropdown,
                db_path_input,
                ft.Divider(color=BORDER_COLOR, height=16),
                ft.Text("RESEARCH RIGOR & DEPTH", size=11, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                depth_radio,
            ], spacing=10),
            width=500,
            padding=10,
        ),
        actions=[
            ft.OutlinedButton("Cancel", on_click=lambda e: (page.pop_dialog(), page.update())),
            ft.FilledButton(
                "Save Preferences",
                style=ft.ButtonStyle(bgcolor=PRIMARY),
                on_click=close_dialog,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=BG_SURFACE,
        shape=ft.RoundedRectangleBorder(radius=12),
    )

    return dialog
