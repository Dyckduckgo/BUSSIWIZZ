"""
Sources Tab Screen
Displays verified primary data sources, SEC filing accession links, and scientific literature.
"""

from typing import Dict, Any, List
import flet as ft
from ui.theme import (
    BG_SURFACE,
    BORDER_COLOR,
    PRIMARY,
    ACCENT_CYAN,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
)


class SourcesTab(ft.Container):
    """Sources verification screen showing grounded regulatory and academic citations."""

    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        self.data = data
        self.build_ui()

    def update_data(self, data: Dict[str, Any]):
        self.data = data
        self.build_ui()
        self.update()

    def build_ui(self):
        sources = self.data.get("sources", [])

        cards = []
        for s in sources:
            title = s.get("title", "Reference Source")
            stype = s.get("type", "Primary Data")
            url = s.get("url", "#")

            icon = ft.Icons.ACCOUNT_BALANCE if "Regulatory" in stype else (
                ft.Icons.MENU_BOOK if "Paper" in stype else ft.Icons.SHOW_CHART
            )

            c = ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(icon, size=18, color=ACCENT_CYAN),
                        bgcolor="#1E293B",
                        padding=10,
                        border_radius=8,
                    ),
                    ft.Column([
                        ft.Row([
                            ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                            ft.Container(
                                content=ft.Text(stype, size=11, color=ACCENT_CYAN, weight=ft.FontWeight.W_600),
                                bgcolor="#083344",
                                padding=ft.Padding(8, 2, 8, 2),
                                border_radius=4,
                            ),
                        ], spacing=8, wrap=True),
                        ft.Text(url, size=11, color=TEXT_MUTED, selectable=True),
                    ], spacing=3, expand=True),
                    ft.IconButton(
                        icon=ft.Icons.OPEN_IN_NEW,
                        icon_size=16,
                        icon_color=TEXT_SECONDARY,
                        url=url,
                        tooltip="Open source URL",
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
                ft.Icon(ft.Icons.LINK_OUTLINED, size=18, color=PRIMARY),
                ft.Text("Verified Primary Sources & Grounded Citations", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ], spacing=8),
            ft.Column(cards, spacing=8),
        ], spacing=12)
