"""
UI Screens Package
Exports dashboard screens and modular tabs for the Stock Research Dashboard.
"""

from .dashboard import DashboardScreen
from .overview_tab import OverviewTab
from .financials_tab import FinancialsTab
from .rnd_tab import RndTab
from .news_tab import NewsTab
from .risks_tab import RisksTab
from .scenarios_tab import ScenariosTab
from .sources_tab import SourcesTab
from .history_tab import HistoryTab
from .settings_modal import create_settings_dialog

__all__ = [
    "DashboardScreen",
    "OverviewTab",
    "FinancialsTab",
    "RndTab",
    "NewsTab",
    "RisksTab",
    "ScenariosTab",
    "SourcesTab",
    "HistoryTab",
    "create_settings_dialog",
]
