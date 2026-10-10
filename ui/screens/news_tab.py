"""
News Tab Screen
Displays recent corporate developments, filings, news headlines, and sentiment analysis.
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


class NewsTab(ft.Container):
    """News and developments screen with sentiment tagging."""

    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        self.data = data
        self.build_ui()

    def update_data(self, data: Dict[str, Any]):
        self.data = data
        self.build_ui()
        self.update()

    def _get_sentiment_badge(self, sentiment: str) -> ft.Container:
        s = sentiment.lower()
        if "bull" in s or "positive" in s:
            bg = "#064E3B"
            fg = SUCCESS_GREEN
            icon = ft.Icons.ARROW_UPWARD
        elif "bear" in s or "negative" in s:
            bg = "#4C0519"
            fg = DANGER_ROSE
            icon = ft.Icons.ARROW_DOWNWARD
        else:
            bg = "#1E293B"
            fg = WARNING_AMBER
            icon = ft.Icons.HORIZONTAL_RULE

        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, size=12, color=fg),
                ft.Text(sentiment, size=11, weight=ft.FontWeight.BOLD, color=fg),
            ], spacing=4),
            bgcolor=bg,
            padding=ft.Padding(8, 2, 8, 2),
            border_radius=6,
        )

    def build_ui(self):
        news_items = self.data.get("news", [])

        cards = []
        for item in news_items:
            title = item.get("title", "Headline")
            date_str = item.get("date", "")
            source = item.get("source", "Market Wire")
            sentiment = item.get("sentiment", "Neutral")
            summary = item.get("summary", "")

            badge = self._get_sentiment_badge(sentiment)

            c = ft.Container(
                content=ft.Column([
                    ft.Row([
                        # Date & Source
                        ft.Row([
                            ft.Icon(ft.Icons.SCHEDULE, size=13, color=TEXT_MUTED),
                            ft.Text(date_str, size=11, color=TEXT_MUTED),
                            ft.Text("•", size=11, color=TEXT_MUTED),
                            ft.Icon(ft.Icons.PUBLIC, size=13, color=ACCENT_CYAN),
                            ft.Text(source, size=11, color=ACCENT_CYAN, weight=ft.FontWeight.W_500),
                        ], spacing=6),
                        badge,
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),
                    ft.Text(title, size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ft.Text(summary, size=12, color=TEXT_SECONDARY),
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
                ft.Icon(ft.Icons.NEWSPAPER_OUTLINED, size=18, color=PRIMARY),
                ft.Text("Curated Corporate News & Regulatory Filings", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
            ], spacing=8),
            ft.Column(cards, spacing=10),
        ], spacing=12)
