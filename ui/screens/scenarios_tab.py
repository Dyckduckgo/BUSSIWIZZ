"""
Bull / Base / Bear Scenarios Tab Screen
Displays 3-tier probabilistic price target valuation models and investment theses.
"""

from typing import Dict, Any
import flet as ft
from ui.theme import (
    BG_SURFACE,
    BORDER_COLOR,
    SUCCESS_GREEN,
    ACCENT_CYAN,
    DANGER_ROSE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
)


class ScenariosTab(ft.Container):
    """Scenario analysis screen showing Bull, Base, and Bear cases."""

    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        self.data = data
        self.build_ui()

    def update_data(self, data: Dict[str, Any]):
        self.data = data
        self.build_ui()
        self.update()

    def _build_scenario_card(
        self,
        case_name: str,
        target_price: str,
        upside: str,
        probability: str,
        thesis: str,
        color: str,
        icon: str,
    ) -> ft.Container:
        is_positive = upside.startswith("+")

        return ft.Container(
            content=ft.Column([
                # Card Header
                ft.Row([
                    ft.Row([
                        ft.Icon(icon, size=18, color=color),
                        ft.Text(case_name, size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ], spacing=6),
                    ft.Container(
                        content=ft.Text(f"Probability: {probability}", size=11, weight=ft.FontWeight.BOLD, color=color),
                        bgcolor="#1E293B",
                        padding=ft.Padding(8, 2, 8, 2),
                        border_radius=6,
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),

                ft.Divider(color=BORDER_COLOR, height=12),

                # Price Target & Upside Pill
                ft.Row([
                    ft.Column([
                        ft.Text("TARGET PRICE", size=10, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                        ft.Text(target_price, size=24, weight=ft.FontWeight.BOLD, color=color),
                    ], spacing=1),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.ARROW_UPWARD if is_positive else ft.Icons.ARROW_DOWNWARD, size=14, color=color),
                            ft.Text(upside, size=13, weight=ft.FontWeight.BOLD, color=color),
                        ], spacing=4),
                        bgcolor="#131B2E",
                        padding=ft.Padding(10, 6, 10, 6),
                        border_radius=8,
                        border=ft.Border(
                            top=ft.BorderSide(1, color),
                            bottom=ft.BorderSide(1, color),
                            left=ft.BorderSide(1, color),
                            right=ft.BorderSide(1, color),
                        ),
                    ),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),

                ft.Container(height=4),
                ft.Text("CORE VALUATION THESIS", size=10, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                ft.Text(thesis, size=12, color=TEXT_SECONDARY, selectable=True),
            ], spacing=8),
            bgcolor=BG_SURFACE,
            border_radius=10,
            padding=16,
            border=ft.Border(
                top=ft.BorderSide(2, color),
                bottom=ft.BorderSide(1, BORDER_COLOR),
                left=ft.BorderSide(1, BORDER_COLOR),
                right=ft.BorderSide(1, BORDER_COLOR),
            ),
            expand=True,
        )

    def build_ui(self):
        scenarios = self.data.get("scenarios", {})
        bull = scenarios.get("bull", {})
        base = scenarios.get("base", {})
        bear = scenarios.get("bear", {})

        bull_card = self._build_scenario_card(
            bull.get("title", "Bull Case"),
            bull.get("target_price", "$320.00"),
            bull.get("upside", "+36.8%"),
            bull.get("probability", "35%"),
            bull.get("thesis", "Blackwell ramp accelerates datacenter sales."),
            SUCCESS_GREEN,
            ft.Icons.TRENDING_UP,
        )

        base_card = self._build_scenario_card(
            base.get("title", "Base Case"),
            base.get("target_price", "$255.00"),
            base.get("upside", "+9.0%"),
            base.get("probability", "50%"),
            base.get("thesis", "Consistent datacenter capex growth with high margins."),
            ACCENT_CYAN,
            ft.Icons.REMOVE,
        )

        bear_card = self._build_scenario_card(
            bear.get("title", "Bear Case"),
            bear.get("target_price", "$175.00"),
            bear.get("upside", "-25.2%"),
            bear.get("probability", "15%"),
            bear.get("thesis", "Hyperscaler capex digestion pause and trade limits."),
            DANGER_ROSE,
            ft.Icons.TRENDING_DOWN,
        )

        # 3 responsive cards in a row
        cards_row = ft.Row([
            bull_card,
            base_card,
            bear_card,
        ], spacing=12, wrap=True)

        self.content = ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.CALL_SPLIT_OUTLINED, size=18, color=ACCENT_CYAN),
                ft.Text("Probabilistic Valuation Framework (12-Month Horizon)", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ], spacing=8),
            cards_row,
        ], spacing=12)
