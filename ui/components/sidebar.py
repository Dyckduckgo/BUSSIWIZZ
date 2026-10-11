"""
Sidebar Component
Houses brand header, ticker/market inputs, research trigger, and settings button.
"""

from typing import Callable, Optional
import flet as ft
from ui.theme import (
    BG_SURFACE,
    BORDER_COLOR,
    PRIMARY,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    ACCENT_CYAN,
)


class Sidebar(ft.Container):
    """Left sidebar navigation and parameter input control."""

    def __init__(
        self,
        on_research: Callable[[str, str, str], None],
        on_settings: Callable[[], None],
        on_cancel: Optional[Callable[[], None]] = None,
        width: int = 300,
    ):
        super().__init__()
        self.width = width
        self.bgcolor = BG_SURFACE
        self.padding = 24
        self.border = ft.Border(right=ft.BorderSide(1, BORDER_COLOR))
        self.on_cancel = on_cancel

        # Inputs
        self.ticker_input = ft.TextField(
            label="Company or Ticker",
            value="NVDA",
            hint_text="e.g. NVDA, Apple, MSFT",
            prefix_icon=ft.Icons.SEARCH,
            text_size=14,
            capitalization=ft.TextCapitalization.CHARACTERS,
        )

        self.market_input = ft.TextField(
            label="Market / Exchange",
            value="NASDAQ",
            hint_text="e.g. NASDAQ, NYSE, LSE",
            prefix_icon=ft.Icons.ACCOUNT_BALANCE,
            text_size=14,
            capitalization=ft.TextCapitalization.CHARACTERS,
        )

        self.email_input = ft.TextField(
            label="Recipient Email",
            value="analyst@firm.com",
            hint_text="e.g. analyst@firm.com",
            prefix_icon=ft.Icons.EMAIL_OUTLINED,
            text_size=14,
        )

        # Buttons
        self.research_btn = ft.FilledButton(
            content=ft.Row([
                ft.Icon(ft.Icons.ROCKET_LAUNCH, size=18),
                ft.Text("Research Company", weight=ft.FontWeight.BOLD),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
            style=ft.ButtonStyle(
                bgcolor=PRIMARY,
                color=TEXT_PRIMARY,
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            height=46,
            on_click=lambda e: on_research(
                self.ticker_input.value.strip(),
                self.market_input.value.strip(),
                self.email_input.value.strip(),
            ),
        )

        self.cancel_btn = ft.OutlinedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.STOP_CIRCLE_OUTLINED, size=18, color="#EF4444"),
                ft.Text("Cancel Research", color="#EF4444", weight=ft.FontWeight.W_600),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, "#7F1D1D"),
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            height=40,
            visible=False,
            on_click=lambda e: on_cancel() if on_cancel else None,
        )

        self.settings_btn = ft.OutlinedButton(
            content=ft.Row([
                ft.Icon(ft.Icons.SETTINGS_OUTLINED, size=18, color=TEXT_SECONDARY),
                ft.Text("Settings", color=TEXT_SECONDARY),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8),
            style=ft.ButtonStyle(
                side=ft.BorderSide(1, BORDER_COLOR),
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            height=40,
            on_click=lambda e: on_settings(),
        )

        # Assemble Sidebar layout
        self.content = ft.Column([
            # Logo & Brand Header
            ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.QUERY_STATS, color=TEXT_PRIMARY, size=24),
                    bgcolor=PRIMARY,
                    border_radius=10,
                    padding=8,
                ),
                ft.Column([
                    ft.Text("AI Stock Research", size=17, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ft.Text("Multi-Agent Intelligence", size=11, color=ACCENT_CYAN),
                ], spacing=1),
            ], spacing=12),

            ft.Divider(color=BORDER_COLOR, height=28),

            # Input Section
            ft.Text("RESEARCH PARAMETERS", size=11, weight=ft.FontWeight.W_600, color=TEXT_MUTED),
            self.ticker_input,
            self.market_input,
            self.email_input,

            ft.Container(height=8),
            self.research_btn,
            self.cancel_btn,

            ft.Container(expand=True),

            # Footer & Settings
            ft.Divider(color=BORDER_COLOR, height=20),
            self.settings_btn,
            ft.Container(height=4),
            ft.Row([
                ft.Icon(ft.Icons.SHIELD_OUTLINED, size=13, color=TEXT_MUTED),
                ft.Text("Local-First Architecture", size=11, color=TEXT_MUTED),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=4),
        ], spacing=12, expand=True)

    def set_loading(self, is_loading: bool):
        """Toggles sidebar button states between interactive and researching/cancel."""
        self.research_btn.disabled = is_loading
        if is_loading:
            self.research_btn.content = ft.Row([
                ft.ProgressRing(width=16, height=16, stroke_width=2, color=TEXT_PRIMARY),
                ft.Text("Researching...", weight=ft.FontWeight.BOLD),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8)
            self.cancel_btn.visible = True
        else:
            self.research_btn.content = ft.Row([
                ft.Icon(ft.Icons.ROCKET_LAUNCH, size=18),
                ft.Text("Research Company", weight=ft.FontWeight.BOLD),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=8)
            self.cancel_btn.visible = False
        self.update()
