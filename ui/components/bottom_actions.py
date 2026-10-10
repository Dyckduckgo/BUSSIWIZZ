"""
Bottom Actions Component
Provides report export controls: "Download PDF" and "Send PDF by Email".
"""

from typing import Callable, Optional
import flet as ft
from ui.theme import (
    BG_SURFACE,
    BORDER_COLOR,
    PRIMARY,
    PRIMARY_HOVER,
    SUCCESS_GREEN,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
)


class BottomActions(ft.Container):
    """Action bar at bottom of dashboard for PDF generation and distribution."""

    def __init__(
        self,
        on_download_pdf: Callable[[], None],
        on_send_email: Callable[[], None],
    ):
        super().__init__()
        self.bgcolor = BG_SURFACE
        self.padding = ft.Padding(20, 14, 20, 14)
        self.border_radius = 12
        self.border = ft.Border(
            top=ft.BorderSide(1, BORDER_COLOR),
            bottom=ft.BorderSide(1, BORDER_COLOR),
            left=ft.BorderSide(1, BORDER_COLOR),
            right=ft.BorderSide(1, BORDER_COLOR),
        )
        self.on_download_pdf = on_download_pdf
        self.on_send_email = on_send_email
        self.build_ui()

    def build_ui(self):
        download_btn = ft.OutlinedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.PICTURE_AS_PDF_OUTLINED, size=18, color=TEXT_PRIMARY),
                ft.Text("Download PDF", weight=ft.FontWeight.W_600, color=TEXT_PRIMARY),
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, BORDER_COLOR),
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            height=44,
            on_click=lambda e: self.on_download_pdf(),
        )

        send_email_btn = ft.FilledButton(
            content=ft.Row([
                ft.Icon(ft.Icons.SEND_ROUNDED, size=17, color=TEXT_PRIMARY),
                ft.Text("Send PDF by Email", weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
            style=ft.ButtonStyle(
                bgcolor=PRIMARY,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            height=44,
            on_click=lambda e: self.on_send_email(),
        )

        self.content = ft.Row([
            # Left: Description & Format
            ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.DESCRIPTION_OUTLINED, size=20, color=TEXT_SECONDARY),
                    bgcolor="#1E293B",
                    padding=8,
                    border_radius=8,
                ),
                ft.Column([
                    ft.Text("REPORT EXPORT & DISTRIBUTION", size=11, weight=ft.FontWeight.BOLD, color=TEXT_MUTED),
                    ft.Text("Ready to generate structured equity research brief with charts & citations.", size=12, color=TEXT_SECONDARY),
                ], spacing=2),
            ], spacing=12),

            # Right: Action Buttons
            ft.Row([
                download_btn,
                send_email_btn,
            ], spacing=10, wrap=True),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER, wrap=True)
