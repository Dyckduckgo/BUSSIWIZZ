"""
Header Component
Displays active target company name, ticker, market, and research date badges.
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


class Header(ft.Container):
    """Main view header showing target company identity and metadata badges."""

    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        self.padding = ft.Padding(20, 16, 20, 16)
        self.bgcolor = BG_SURFACE
        self.border_radius = 12
        self.border = ft.Border(
            top=ft.BorderSide(1, BORDER_COLOR),
            bottom=ft.BorderSide(1, BORDER_COLOR),
            left=ft.BorderSide(1, BORDER_COLOR),
            right=ft.BorderSide(1, BORDER_COLOR),
        )
        self.data = data
        self.build_ui()

    def update_data(self, data: Dict[str, Any]):
        self.data = data
        self.build_ui()
        self.update()

    def build_ui(self):
        company_name = self.data.get("company", "NVIDIA Corporation")
        ticker = self.data.get("ticker", "NVDA")
        market = self.data.get("market", "NASDAQ: US")
        research_date = self.data.get("research_date", "October 04, 2026")

        self.content = ft.Row([
            # Left: Company Title & Ticker
            ft.Column([
                ft.Row([
                    ft.Text(company_name, size=24, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    # Ticker Badge
                    ft.Container(
                        content=ft.Text(ticker, size=12, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        bgcolor=PRIMARY,
                        padding=ft.Padding(8, 2, 8, 2),
                        border_radius=6,
                    ),
                    # Market Badge
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.ACCOUNT_BALANCE, size=13, color=ACCENT_CYAN),
                            ft.Text(market, size=11, weight=ft.FontWeight.W_600, color=ACCENT_CYAN),
                        ], spacing=4),
                        bgcolor="#083344",
                        padding=ft.Padding(8, 3, 8, 3),
                        border_radius=6,
                        border=ft.Border(
                            top=ft.BorderSide(1, "#0E7490"),
                            bottom=ft.BorderSide(1, "#0E7490"),
                            left=ft.BorderSide(1, "#0E7490"),
                            right=ft.BorderSide(1, "#0E7490"),
                        ),
                    ),
                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True),
                ft.Text("Autonomous Multimodal Research & Valuation Analysis", size=12, color=TEXT_MUTED),
            ], spacing=2, expand=True),

            # Right: Date & Status Badge
            ft.Row([
                # Date Chip
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED, size=13, color=TEXT_SECONDARY),
                        ft.Text(research_date, size=12, color=TEXT_SECONDARY),
                    ], spacing=6),
                    bgcolor="#1E293B",
                    padding=ft.Padding(10, 6, 10, 6),
                    border_radius=8,
                ),
                # Status Chip
                ft.Container(
                    content=ft.Row([
                        ft.Container(width=8, height=8, bgcolor=SUCCESS_GREEN, border_radius=4),
                        ft.Text("Report Ready", size=12, weight=ft.FontWeight.W_600, color=SUCCESS_GREEN),
                    ], spacing=6),
                    bgcolor="#064E3B",
                    padding=ft.Padding(10, 6, 10, 6),
                    border_radius=8,
                    border=ft.Border(
                        top=ft.BorderSide(1, SUCCESS_GREEN),
                        bottom=ft.BorderSide(1, SUCCESS_GREEN),
                        left=ft.BorderSide(1, SUCCESS_GREEN),
                        right=ft.BorderSide(1, SUCCESS_GREEN),
                    ),
                ),
            ], spacing=8, wrap=True),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True)
