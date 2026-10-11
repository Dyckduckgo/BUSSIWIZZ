"""
Progress Panel Component
Displays stage-by-stage execution status across the 6 research pipelines:
1. Web Research
2. Financial Analysis
3. SEC Research
4. R&D Research
5. Verification
6. Final Analysis
"""

from typing import Dict, Any, List
import flet as ft
from ui.theme import (
    BG_SURFACE,
    BORDER_COLOR,
    SUCCESS_GREEN,
    ACCENT_CYAN,
    PRIMARY,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
)


class ProgressPanel(ft.Container):
    """Panel showing progress for the 6 core research stages."""

    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        self.data = data
        self.bgcolor = BG_SURFACE
        self.border_radius = 12
        self.padding = 16
        self.border = ft.Border(
            top=ft.BorderSide(1, BORDER_COLOR),
            bottom=ft.BorderSide(1, BORDER_COLOR),
            left=ft.BorderSide(1, BORDER_COLOR),
            right=ft.BorderSide(1, BORDER_COLOR),
        )
        self.is_expanded = True
        self.build_ui()

    def update_data(self, data: Dict[str, Any]):
        self.data = data
        self.build_ui()
        self.update()

    def toggle_expand(self, e):
        self.is_expanded = not self.is_expanded
        self.build_ui()
        self.update()

    def build_ui(self):
        default_steps = [
            {"step": "Web Research", "status": "Completed", "detail": "Gathered recent market intelligence and corporate filings."},
            {"step": "Financial Analysis", "status": "Completed", "detail": "Verified key fundamental valuation metrics and margins."},
            {"step": "SEC Research", "status": "Completed", "detail": "Parsed official corporate disclosures and 10-K/10-Q filings."},
            {"step": "R&D Research", "status": "Completed", "detail": "Surveyed strategic technology roadmap and patent activity."},
            {"step": "Verification", "status": "Completed", "detail": "Cross-referenced all evidence against primary financial sources."},
            {"step": "Final Analysis", "status": "Completed", "detail": "Synthesized multi-factor scorecard and Bull/Base/Bear scenarios."},
        ]
        steps = self.data.get("progress_steps") or default_steps

        # Step Tiles
        tiles = []
        completed_count = 0
        in_progress_count = 0

        for i, item in enumerate(steps, 1):
            name = item.get("step", f"Stage {i}")
            status = item.get("status", "Pending")
            detail = item.get("detail", "Analysis pending.")
            st_lower = status.lower()

            if st_lower in ["running", "in progress"]:
                in_progress_count += 1
                icon_widget = ft.ProgressRing(width=14, height=14, stroke_width=2, color="#38BDF8")
                icon_bg = "#0C4A6E"
                status_color = "#38BDF8"
            elif st_lower in ["completed", "complete", "success"]:
                completed_count += 1
                icon_widget = ft.Icon(ft.Icons.CHECK, size=14, color=SUCCESS_GREEN)
                icon_bg = "#064E3B"
                status_color = SUCCESS_GREEN
            elif st_lower in ["failed", "error", "timeout"]:
                icon_widget = ft.Icon(ft.Icons.ERROR_OUTLINE, size=14, color="#EF4444")
                icon_bg = "#450A0A"
                status_color = "#EF4444"
            elif st_lower in ["cancelled", "canceled"]:
                icon_widget = ft.Icon(ft.Icons.CANCEL_OUTLINED, size=14, color="#F59E0B")
                icon_bg = "#451A03"
                status_color = "#F59E0B"
            else:  # Pending
                icon_widget = ft.Icon(ft.Icons.SCHEDULE, size=14, color=TEXT_MUTED)
                icon_bg = "#1E293B"
                status_color = TEXT_MUTED

            tile = ft.Container(
                content=ft.Row([
                    # Stage Icon / Spinner
                    ft.Container(
                        content=icon_widget,
                        bgcolor=icon_bg,
                        border_radius=12,
                        padding=4,
                    ),
                    ft.Column([
                        ft.Row([
                            ft.Text(f"{i}. {name}", size=12, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                            ft.Text(f"• {status}", size=11, color=status_color, weight=ft.FontWeight.W_600),
                        ], spacing=6),
                        ft.Text(detail, size=11, color=TEXT_MUTED, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ], spacing=1, expand=True),
                ], spacing=10),
                bgcolor="#131B2E",
                border_radius=8,
                padding=ft.Padding(10, 8, 10, 8),
                border=ft.Border(
                    top=ft.BorderSide(1, "#1E293B"),
                    bottom=ft.BorderSide(1, "#1E293B"),
                    left=ft.BorderSide(1, "#1E293B"),
                    right=ft.BorderSide(1, "#1E293B"),
                ),
                expand=True,
            )
            tiles.append(tile)

        # 2 rows of 3 columns
        row1 = ft.Row(tiles[:3], spacing=10)
        row2 = ft.Row(tiles[3:], spacing=10)

        progress_ratio = completed_count / max(len(steps), 1)

        if completed_count == len(steps):
            badge_text = "100% Complete"
            badge_bg = "#064E3B"
            badge_fg = SUCCESS_GREEN
            bar_color = SUCCESS_GREEN
        elif in_progress_count > 0:
            badge_text = f"Live: Stage {completed_count + 1} of {len(steps)}"
            badge_bg = "#0C4A6E"
            badge_fg = "#38BDF8"
            bar_color = "#38BDF8"
        elif any(s.get("status", "").lower() in ["failed", "error", "timeout"] for s in steps):
            badge_text = "Stage Interrupted"
            badge_bg = "#450A0A"
            badge_fg = "#EF4444"
            bar_color = "#EF4444"
        else:
            badge_text = f"{completed_count}/{len(steps)} Complete"
            badge_bg = "#1E293B"
            badge_fg = TEXT_MUTED
            bar_color = PRIMARY

        header_row = ft.Row([
            ft.Row([
                ft.Icon(ft.Icons.AUTO_AWESOME, size=16, color=PRIMARY),
                ft.Text("RESEARCH EXECUTION PIPELINE", size=12, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                ft.Container(
                    content=ft.Text(badge_text, size=11, weight=ft.FontWeight.BOLD, color=badge_fg),
                    bgcolor=badge_bg,
                    padding=ft.Padding(6, 2, 6, 2),
                    border_radius=4,
                ),
            ], spacing=8),
            ft.IconButton(
                icon=ft.Icons.KEYBOARD_ARROW_UP if self.is_expanded else ft.Icons.KEYBOARD_ARROW_DOWN,
                icon_size=18,
                icon_color=TEXT_MUTED,
                on_click=self.toggle_expand,
                tooltip="Collapse/Expand Progress Panel",
            ),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        elements = [header_row]
        if self.is_expanded:
            elements.extend([
                ft.ProgressBar(value=progress_ratio, color=bar_color, bgcolor="#1E293B", height=4),
                row1,
                row2,
            ])

        self.content = ft.Column(elements, spacing=8)
