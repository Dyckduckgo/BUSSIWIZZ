"""
History Tab Screen
Displays past research dossiers and allows reloading previous corporate reports.
"""

from typing import Dict, Any, List, Callable, Optional
import flet as ft
from ui.theme import (
    BG_SURFACE,
    BORDER_COLOR,
    PRIMARY,
    SUCCESS_GREEN,
    ACCENT_CYAN,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
)


class HistoryTab(ft.Container):
    """Past research sessions audit log and dossier loader."""

    def __init__(self, data: Dict[str, Any], on_load_session: Optional[Callable[[str], None]] = None):
        super().__init__()
        self.data = data
        self.on_load_session = on_load_session
        self.build_ui()

    def update_data(self, data: Dict[str, Any]):
        self.data = data
        self.build_ui()
        self.update()

    def build_ui(self):
        history = self.data.get("history", [])

        cards = []
        for item in history:
            sess_id = item.get("session_id", "")
            comp = item.get("company", "Company")
            tick = item.get("ticker", "TICK")
            dt = item.get("date", "")
            sc = item.get("score", 85)
            st = item.get("status", "Completed")

            def make_click_handler(ticker_to_load: str):
                return lambda e: self.on_load_session(ticker_to_load) if self.on_load_session else None

            c = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Column([
                            ft.Text(str(sc), size=18, weight=ft.FontWeight.BOLD, color=SUCCESS_GREEN),
                            ft.Text("SCORE", size=9, color=TEXT_MUTED),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                        bgcolor="#064E3B",
                        padding=ft.Padding(12, 6, 12, 6),
                        border_radius=8,
                    ),
                    ft.Column([
                        ft.Row([
                            ft.Text(comp, size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                            ft.Container(
                                content=ft.Text(tick, size=11, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                                bgcolor=PRIMARY,
                                padding=ft.Padding(6, 1, 6, 1),
                                border_radius=4,
                            ),
                            ft.Text(f"• {dt}", size=11, color=TEXT_MUTED),
                        ], spacing=8, wrap=True),
                        ft.Text(f"Session ID: {sess_id}", size=11, color=TEXT_MUTED),
                    ], spacing=2, expand=True),
                    ft.OutlinedButton(
                        content=ft.Row([
                            ft.Icon(ft.Icons.REPLAY, size=14, color=TEXT_PRIMARY),
                            ft.Text("Load", size=12, color=TEXT_PRIMARY),
                        ], spacing=4),
                        style=ft.ButtonStyle(
                            side=ft.BorderSide(1, BORDER_COLOR),
                            shape=ft.RoundedRectangleBorder(radius=6),
                        ),
                        height=32,
                        on_click=make_click_handler(tick),
                    ),
                ], spacing=12),
                bgcolor=BG_SURFACE,
                border_radius=8,
                padding=12,
                border=ft.Border(
                    top=ft.BorderSide(1, BORDER_COLOR),
                    bottom=ft.BorderSide(1, BORDER_COLOR),
                    left=ft.BorderSide(1, BORDER_COLOR),
                    right=ft.BorderSide(1, BORDER_COLOR),
                ),
            )
            cards.append(c)

        self.content = ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.HISTORY_OUTLINED, size=18, color=PRIMARY),
                ft.Text("Previous Research Sessions in Local Database", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ], spacing=8),
            ft.Column(cards, spacing=8),
        ], spacing=12)
