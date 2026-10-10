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
        steps = self.data.get("progress_steps", [])

        # Step Tiles
        tiles = []
        for i, item in enumerate(steps, 1):
            name = item.get("step", f"Stage {i}")
            status = item.get("status", "Completed")
            detail = item.get("detail", "Analysis complete.")

            tile = ft.Container(
                content=ft.Row([
                    # Stage Icon / Number
                    ft.Container(
                        content=ft.Icon(ft.Icons.CHECK, size=14, color=SUCCESS_GREEN),
                        bgcolor="#064E3B",
                        border_radius=12,
                        padding=4,
                    ),
                    ft.Column([
                        ft.Row([
                            ft.Text(f"{i}. {name}", size=12, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                            ft.Text(f"• {status}", size=11, color=SUCCESS_GREEN, weight=ft.FontWeight.W_600),
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
        row1 = ft.Row(tiles[:3], spacing=10, wrap=True)
        row2 = ft.Row(tiles[3:], spacing=10, wrap=True)

        header_row = ft.Row([
            ft.Row([
                ft.Icon(ft.Icons.AUTO_AWESOME, size=16, color=PRIMARY),
                ft.Text("RESEARCH EXECUTION PIPELINE", size=12, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                ft.Container(
                    content=ft.Text("100% Complete", size=11, weight=ft.FontWeight.BOLD, color=SUCCESS_GREEN),
                    bgcolor="#064E3B",
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
                ft.ProgressBar(value=1.0, color=SUCCESS_GREEN, bgcolor="#1E293B", height=4),
                row1,
                row2,
            ])

        self.content = ft.Column(elements, spacing=8)
