"""
Navigation Component
Horizontal tab bar for switching between research sections.
Tabs: Overview, Financials, R&D, News, Risks, Bull / Base / Bear, Sources, History.
"""

from typing import Callable, List, Tuple
import flet as ft
from ui.theme import (
    BG_SURFACE,
    BORDER_COLOR,
    PRIMARY,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
)

TABS: List[Tuple[str, str, str]] = [
    ("overview", "Overview", ft.Icons.DASHBOARD_OUTLINED),
    ("financials", "Financials", ft.Icons.TABLE_CHART_OUTLINED),
    ("rnd", "R&D", ft.Icons.BIOTECH_OUTLINED),
    ("news", "News", ft.Icons.NEWSPAPER_OUTLINED),
    ("risks", "Risks", ft.Icons.WARNING_AMBER_OUTLINED),
    ("scenarios", "Bull / Base / Bear", ft.Icons.CALL_SPLIT_OUTLINED),
    ("sources", "Sources", ft.Icons.LINK_OUTLINED),
    ("history", "History", ft.Icons.HISTORY_OUTLINED),
]


class Navigation(ft.Container):
    """Horizontal navigation tabs container with active tab highlighting."""

    def __init__(self, on_tab_change: Callable[[str], None], active_tab: str = "overview"):
        super().__init__()
        self.on_tab_change = on_tab_change
        self.active_tab = active_tab
        self.bgcolor = BG_SURFACE
        self.border_radius = 10
        self.padding = ft.Padding(6, 6, 6, 6)
        self.border = ft.Border(
            top=ft.BorderSide(1, BORDER_COLOR),
            bottom=ft.BorderSide(1, BORDER_COLOR),
            left=ft.BorderSide(1, BORDER_COLOR),
            right=ft.BorderSide(1, BORDER_COLOR),
        )
        self.build_ui()

    def set_active_tab(self, tab_key: str):
        self.active_tab = tab_key
        self.build_ui()
        self.update()

    def build_ui(self):
        buttons = []
        for key, label, icon in TABS:
            is_active = key == self.active_tab
            bg = PRIMARY if is_active else "transparent"
            fg = TEXT_PRIMARY if is_active else TEXT_SECONDARY

            def make_handler(k):
                return lambda e: self._handle_click(k)

            btn = ft.Container(
                content=ft.Row([
                    ft.Icon(icon, size=15, color=fg),
                    ft.Text(label, size=12, weight=ft.FontWeight.W_600 if is_active else ft.FontWeight.NORMAL, color=fg),
                ], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
                bgcolor=bg,
                border_radius=7,
                padding=ft.Padding(12, 8, 12, 8),
                on_click=make_handler(key),
                animate=ft.Animation(150, ft.AnimationCurve.EASE_IN_OUT),
            )
            buttons.append(btn)

        self.content = ft.Row(
            controls=buttons,
            spacing=4,
            wrap=True,
            alignment=ft.MainAxisAlignment.START,
        )

    def _handle_click(self, tab_key: str):
        self.active_tab = tab_key
        self.build_ui()
        self.update()
        self.on_tab_change(tab_key)
