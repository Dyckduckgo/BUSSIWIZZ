"""
Dashboard Screen
Master dashboard container that orchestrates Header, ScoreCard, Navigation,
Tab Content Screens, ProgressPanel, and BottomActions.
"""

from typing import Dict, Any, Callable, Optional
import flet as ft

from ui.components.header import Header
from ui.components.score_card import ScoreCard
from ui.components.navigation import Navigation
from ui.components.progress_panel import ProgressPanel
from ui.components.bottom_actions import BottomActions

from ui.screens.overview_tab import OverviewTab
from ui.screens.financials_tab import FinancialsTab
from ui.screens.rnd_tab import RndTab
from ui.screens.news_tab import NewsTab
from ui.screens.risks_tab import RisksTab
from ui.screens.scenarios_tab import ScenariosTab
from ui.screens.sources_tab import SourcesTab
from ui.screens.history_tab import HistoryTab
from ui.theme import BG_DARK


class DashboardScreen(ft.Container):
    """Main scrollable research workspace displaying analytical components and tabs."""

    def __init__(
        self,
        data: Dict[str, Any],
        on_download_pdf: Callable[[], None],
        on_send_email: Callable[[], None],
        on_load_session: Optional[Callable[[str], None]] = None,
    ):
        super().__init__()
        self.data = data
        self.on_download_pdf = on_download_pdf
        self.on_send_email = on_send_email
        self.on_load_session = on_load_session
        self.active_tab = "overview"

        self.bgcolor = BG_DARK
        self.padding = ft.Padding(24, 20, 24, 24)
        self.expand = True

        # Initialize Child Components
        self.header = Header(self.data)
        self.score_card = ScoreCard(self.data)
        self.navigation = Navigation(on_tab_change=self.handle_tab_change, active_tab="overview")
        self.progress_panel = ProgressPanel(self.data)
        self.bottom_actions = BottomActions(
            on_download_pdf=self.on_download_pdf,
            on_send_email=self.on_send_email,
        )

        # Tab Content Container
        self.tab_container = ft.Container()
        self._update_tab_content()

        # Build Main Scrollable Content
        self.scroll_column = ft.Column([
            self.header,
            self.score_card,
            self.navigation,
            self.tab_container,
            self.progress_panel,
            self.bottom_actions,
        ], spacing=16, scroll=ft.ScrollMode.AUTO, expand=True)

        self.content = self.scroll_column

    def handle_tab_change(self, tab_key: str):
        self.active_tab = tab_key
        self._update_tab_content()
        self.tab_container.update()

    def _update_tab_content(self):
        if self.active_tab == "overview":
            self.tab_container.content = OverviewTab(self.data)
        elif self.active_tab == "financials":
            self.tab_container.content = FinancialsTab(self.data)
        elif self.active_tab == "rnd":
            self.tab_container.content = RndTab(self.data)
        elif self.active_tab == "news":
            self.tab_container.content = NewsTab(self.data)
        elif self.active_tab == "risks":
            self.tab_container.content = RisksTab(self.data)
        elif self.active_tab == "scenarios":
            self.tab_container.content = ScenariosTab(self.data)
        elif self.active_tab == "sources":
            self.tab_container.content = SourcesTab(self.data)
        elif self.active_tab == "history":
            self.tab_container.content = HistoryTab(self.data, on_load_session=self.on_load_session)
        else:
            self.tab_container.content = OverviewTab(self.data)

    def update_data(self, data: Dict[str, Any]):
        """Refreshes all nested components with fresh research dataset."""
        self.data = data
        self.header.update_data(data)
        self.score_card.update_data(data)
        self.progress_panel.update_data(data)
        self._update_tab_content()
        self.tab_container.update()
