"""
Risks Tab Screen
Displays categorized risk matrices, severity levels, and structural vulnerabilities.
"""

from typing import Dict, Any, List
import flet as ft
from ui.theme import (
    BG_SURFACE,
    BORDER_COLOR,
    PRIMARY,
    SUCCESS_GREEN,
    WARNING_AMBER,
    DANGER_ROSE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
)


class RisksTab(ft.Container):
    """Risks assessment matrix screen."""

    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        self.data = data
        self.build_ui()

    def update_data(self, data: Dict[str, Any]):
        self.data = data
        self.build_ui()
        self.update()

    def _get_severity_chip(self, severity: str) -> ft.Container:
        s = severity.lower()
        if "high" in s:
            bg = "#4C0519"
            fg = DANGER_ROSE
        elif "med" in s:
            bg = "#451A03"
            fg = WARNING_AMBER
        else:
            bg = "#064E3B"
            fg = SUCCESS_GREEN

        return ft.Container(
            content=ft.Row([
                ft.Container(width=6, height=6, bgcolor=fg, border_radius=3),
                ft.Text(f"{severity} Severity", size=11, weight=ft.FontWeight.BOLD, color=fg),
            ], spacing=6),
            bgcolor=bg,
            padding=ft.Padding(8, 2, 8, 2),
            border_radius=6,
        )

    def build_ui(self):
        risks = self.data.get("risks", [])

        cards = []
        for r in risks:
            cat = r.get("category", "General Risk")
            sev = r.get("severity", "Medium")
            like = r.get("likelihood", "Moderate")
            detail = r.get("detail", "")

            sev_chip = self._get_severity_chip(sev)

            c = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Row([
                            ft.Icon(ft.Icons.REPORT_PROBLEM_OUTLINED, size=16, color=WARNING_AMBER),
                            ft.Text(cat, size=13, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                        ], spacing=6),
                        ft.Row([
                            ft.Container(
                                content=ft.Text(f"Likelihood: {like}", size=11, color=TEXT_MUTED),
                                bgcolor="#1E293B",
                                padding=ft.Padding(6, 2, 6, 2),
                                border_radius=4,
                            ),
                            sev_chip,
                        ], spacing=6),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),
                    ft.Text(detail, size=12, color=TEXT_SECONDARY),
                ], spacing=6),
                bgcolor=BG_SURFACE,
                border_radius=8,
                padding=14,
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
                ft.Icon(ft.Icons.WARNING_AMBER_OUTLINED, size=18, color=WARNING_AMBER),
                ft.Text("Categorized Risk Matrix & Downside Factors", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ], spacing=8),
            ft.Column(cards, spacing=10),
        ], spacing=12)
