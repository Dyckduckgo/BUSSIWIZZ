"""
Score Card Component
Displays high-level research score and 7-dimension evaluation metrics.
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
    ACCENT_CYAN,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
)


class ScoreCard(ft.Container):
    """Evaluation score dashboard showing Overall Score and 7 dimension breakdown cards."""

    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        self.data = data
        self.build_ui()

    def update_data(self, data: Dict[str, Any]):
        self.data = data
        self.build_ui()
        self.update()

    def _get_score_color(self, score: int, is_risk: bool = False) -> str:
        if is_risk:
            # For risk: lower is safer
            if score <= 45:
                return SUCCESS_GREEN
            elif score <= 70:
                return WARNING_AMBER
            return DANGER_ROSE

        if score >= 85:
            return SUCCESS_GREEN
        elif score >= 70:
            return ACCENT_CYAN
        elif score >= 50:
            return WARNING_AMBER
        return DANGER_ROSE

    def _build_metric_tile(self, label: str, score: int, icon: str, is_risk: bool = False) -> ft.Container:
        color = self._get_score_color(score, is_risk)
        progress_val = score / 100.0

        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Row([
                        ft.Icon(icon, size=15, color=color),
                        ft.Text(label, size=12, weight=ft.FontWeight.W_600, color=TEXT_SECONDARY),
                    ], spacing=6),
                    ft.Text(f"{score}/100", size=13, weight=ft.FontWeight.BOLD, color=color),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.ProgressBar(value=progress_val, color=color, bgcolor="#1E293B", height=5),
            ], spacing=6),
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
        scores = self.data.get("scores", {})
        score_details = self.data.get("score_details", {})

        overall_score = scores.get("overall", 88)
        overall_color = self._get_score_color(overall_score)
        grade_text = score_details.get("overall_grade", "A - Strong Buy / High Conviction")
        verdict_text = score_details.get("verdict", "Unrivaled competitive moat in accelerated computing.")

        # Main Overall Score Hero Card
        overall_hero = ft.Container(
            content=ft.Row([
                # Score Circle / Pill
                ft.Container(
                    content=ft.Column([
                        ft.Text(str(overall_score), size=36, weight=ft.FontWeight.BOLD, color=overall_color),
                        ft.Text("/100", size=12, color=TEXT_MUTED),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
                    bgcolor="#0D1A30",
                    border_radius=16,
                    padding=ft.Padding(16, 12, 16, 12),
                    border=ft.Border(
                        top=ft.BorderSide(2, overall_color),
                        bottom=ft.BorderSide(2, overall_color),
                        left=ft.BorderSide(2, overall_color),
                        right=ft.BorderSide(2, overall_color),
                    ),
                    alignment=ft.Alignment.CENTER,
                ),
                # Details
                ft.Column([
                    ft.Row([
                        ft.Text("OVERALL RESEARCH SCORE", size=12, weight=ft.FontWeight.W_700, color=TEXT_MUTED),
                        ft.Container(
                            content=ft.Text(grade_text, size=11, weight=ft.FontWeight.BOLD, color=SUCCESS_GREEN),
                            bgcolor="#064E3B",
                            padding=ft.Padding(8, 2, 8, 2),
                            border_radius=6,
                        ),
                    ], spacing=10, wrap=True),
                    ft.Text(verdict_text, size=13, color=TEXT_SECONDARY, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                ], spacing=4, expand=True),
            ], spacing=20, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=BG_SURFACE,
            border_radius=12,
            padding=18,
            border=ft.Border(
                top=ft.BorderSide(1, BORDER_COLOR),
                bottom=ft.BorderSide(1, BORDER_COLOR),
                left=ft.BorderSide(1, BORDER_COLOR),
                right=ft.BorderSide(1, BORDER_COLOR),
            ),
        )

        # 7 Dimension Tiles (arranged in 2 responsive rows)
        row1 = ft.Row([
            self._build_metric_tile("Business Quality", scores.get("business_quality", 94), ft.Icons.VERIFIED_OUTLINED),
            self._build_metric_tile("Financial Health", scores.get("financial_health", 91), ft.Icons.FAVORITE_BORDER),
            self._build_metric_tile("Growth Momentum", scores.get("growth", 96), ft.Icons.TRENDING_UP),
            self._build_metric_tile("Competitive Advantage", scores.get("competitive_advantage", 95), ft.Icons.SHIELD_OUTLINED),
        ], spacing=10)

        row2 = ft.Row([
            self._build_metric_tile("Valuation Score", scores.get("valuation", 68), ft.Icons.PRICE_CHECK_OUTLINED),
            self._build_metric_tile("R&D & Innovation", scores.get("rnd", 92), ft.Icons.SCIENCE_OUTLINED),
            self._build_metric_tile("Risk Assessment", scores.get("risk", 42), ft.Icons.WARNING_AMBER_OUTLINED, is_risk=True),
        ], spacing=10)

        self.content = ft.Column([
            overall_hero,
            row1,
            row2,
        ], spacing=10)
