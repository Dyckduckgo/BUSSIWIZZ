"""
Overview Tab Screen
Displays business description, corporate facts, executive summary, and economic moat analysis.
"""

from typing import Dict, Any
import flet as ft
from ui.theme import (
    BG_SURFACE,
    BORDER_COLOR,
    PRIMARY,
    ACCENT_CYAN,
    SUCCESS_GREEN,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
)


class OverviewTab(ft.Container):
    """Overview screen presenting corporate profile and economic moat."""

    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        self.data = data
        self.build_ui()

    def update_data(self, data: Dict[str, Any]):
        self.data = data
        self.build_ui()
        self.update()

    def _build_info_tile(self, label: str, value: str, icon: str) -> ft.Container:
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, size=16, color=ACCENT_CYAN),
                ft.Column([
                    ft.Text(label, size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_500),
                    ft.Text(value, size=13, weight=ft.FontWeight.W_600, color=TEXT_PRIMARY),
                ], spacing=1),
            ], spacing=10),
            bgcolor="#131B2E",
            border_radius=8,
            padding=ft.Padding(12, 10, 12, 10),
            border=ft.Border(
                top=ft.BorderSide(1, BORDER_COLOR),
                bottom=ft.BorderSide(1, BORDER_COLOR),
                left=ft.BorderSide(1, BORDER_COLOR),
                right=ft.BorderSide(1, BORDER_COLOR),
            ),
            expand=True,
        )

    def build_ui(self):
        overview = self.data.get("overview", {})
        description = overview.get("description", "No description available.")
        moat = overview.get("moat", "Competitive moat analysis pending.")

        # Corporate Metadata Tiles (2 rows of 3)
        row1 = ft.Row([
            self._build_info_tile("LEADERSHIP", overview.get("ceo", "Jensen Huang"), ft.Icons.PERSON_OUTLINED),
            self._build_info_tile("FOUNDED", overview.get("founded", "1993"), ft.Icons.EVENT_OUTLINED),
            self._build_info_tile("HEADQUARTERS", overview.get("headquarters", "Santa Clara, CA"), ft.Icons.LOCATION_ON_OUTLINED),
        ], spacing=10)

        row2 = ft.Row([
            self._build_info_tile("EMPLOYEES", overview.get("employees", "29,600+"), ft.Icons.GROUPS_OUTLINED),
            self._build_info_tile("SECTOR", overview.get("sector", "Information Technology"), ft.Icons.CATEGORY_OUTLINED),
            self._build_info_tile("INDUSTRY", overview.get("industry", "Semiconductors"), ft.Icons.MEMORY_OUTLINED),
        ], spacing=10)

        # Company Description Card
        desc_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.BUSINESS_OUTLINED, size=18, color=PRIMARY),
                    ft.Text("Business Summary & Model", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                ], spacing=8),
                ft.Text(description, size=13, color=TEXT_SECONDARY, selectable=True),
            ], spacing=10),
            bgcolor=BG_SURFACE,
            border_radius=10,
            padding=16,
            border=ft.Border(
                top=ft.BorderSide(1, BORDER_COLOR),
                bottom=ft.BorderSide(1, BORDER_COLOR),
                left=ft.BorderSide(1, BORDER_COLOR),
                right=ft.BorderSide(1, BORDER_COLOR),
            ),
        )

        # Economic Moat Card
        moat_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.FORT_OUTLINED, size=18, color=SUCCESS_GREEN),
                    ft.Text("Economic Moat & Competitive Advantages", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ft.Container(
                        content=ft.Text("Wide Moat", size=11, weight=ft.FontWeight.BOLD, color=SUCCESS_GREEN),
                        bgcolor="#064E3B",
                        padding=ft.Padding(8, 2, 8, 2),
                        border_radius=6,
                    ),
                ], spacing=8),
                ft.Text(moat, size=13, color=TEXT_SECONDARY, selectable=True),
            ], spacing=10),
            bgcolor=BG_SURFACE,
            border_radius=10,
            padding=16,
            border=ft.Border(
                top=ft.BorderSide(1, BORDER_COLOR),
                bottom=ft.BorderSide(1, BORDER_COLOR),
                left=ft.BorderSide(1, BORDER_COLOR),
                right=ft.BorderSide(1, BORDER_COLOR),
            ),
        )

        self.content = ft.Column([
            row1,
            row2,
            desc_card,
            moat_card,
        ], spacing=12)
