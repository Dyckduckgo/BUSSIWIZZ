"""
R&D Tab Screen
Displays research & development investment metrics, patent portfolios, and technological roadmaps.
"""

from typing import Dict, Any, List
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


class RndTab(ft.Container):
    """R&D innovation and intellectual property screen."""

    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        self.data = data
        self.build_ui()

    def update_data(self, data: Dict[str, Any]):
        self.data = data
        self.build_ui()
        self.update()

    def _build_stat_tile(self, label: str, value: str, subtext: str, icon: str) -> ft.Container:
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icon, size=22, color=PRIMARY),
                    bgcolor="#1E293B",
                    padding=10,
                    border_radius=8,
                ),
                ft.Column([
                    ft.Text(label, size=11, color=TEXT_MUTED, weight=ft.FontWeight.W_600),
                    ft.Text(value, size=16, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ft.Text(subtext, size=11, color=TEXT_SECONDARY),
                ], spacing=2),
            ], spacing=12),
            bgcolor="#131B2E",
            border_radius=8,
            padding=ft.Padding(14, 12, 14, 12),
            border=ft.Border(
                top=ft.BorderSide(1, BORDER_COLOR),
                bottom=ft.BorderSide(1, BORDER_COLOR),
                left=ft.BorderSide(1, BORDER_COLOR),
                right=ft.BorderSide(1, BORDER_COLOR),
            ),
            expand=True,
        )

    def build_ui(self):
        rnd = self.data.get("rnd", {})
        initiatives = rnd.get("key_initiatives", [])

        # Stats Row
        stats_row = ft.Row([
            self._build_stat_tile(
                "ANNUAL R&D EXPENDITURE",
                rnd.get("annual_spend", "$11.20B (12.4% of rev)"),
                "Reinvested into next-gen silicon & AI software",
                ft.Icons.SAVINGS_OUTLINED,
            ),
            self._build_stat_tile(
                "GLOBAL PATENT PORTFOLIO",
                rnd.get("patents_granted", "2,850+ Patent Families"),
                "Proprietary IP covering microarchitecture & interconnect",
                ft.Icons.WORKSPACE_PREMIUM_OUTLINED,
            ),
            self._build_stat_tile(
                "ENGINEERING HEADCOUNT",
                rnd.get("rd_headcount", "19,500+ Engineers"),
                "Over 65% of entire enterprise workforce in R&D",
                ft.Icons.ENGINEERING_OUTLINED,
            ),
        ], spacing=10, wrap=True)

        # Strategic Innovation Initiatives Cards
        cards = []
        for item in initiatives:
            name = item.get("name", "Project")
            status = item.get("status", "Active")
            impact = item.get("impact", "")

            status_bg = "#064E3B" if "Production" in status or "Commercialized" in status else "#1E293B"
            status_fg = SUCCESS_GREEN if "Production" in status or "Commercialized" in status else ACCENT_CYAN

            c = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Row([
                            ft.Icon(ft.Icons.LIGHTBULB_OUTLINED, size=16, color=PRIMARY),
                            ft.Text(name, size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ], spacing=6),
                        ft.Container(
                            content=ft.Text(status, size=11, weight=ft.FontWeight.W_600, color=status_fg),
                            bgcolor=status_bg,
                            padding=ft.Padding(8, 2, 8, 2),
                            border_radius=6,
                        ),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),
                    ft.Text(impact, size=12, color=TEXT_SECONDARY),
                ], spacing=6),
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

        initiatives_container = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.ROCKET_LAUNCH_OUTLINED, size=18, color=PRIMARY),
                    ft.Text("Strategic Technology & Roadmap Initiatives", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                ], spacing=8),
                ft.Column(cards, spacing=8),
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
            stats_row,
            initiatives_container,
        ], spacing=12)
