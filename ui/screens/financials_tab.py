"""
Financials Tab Screen
Displays 15 core financial metrics, valuation multiples, margin trends, and quarterly earnings data.
"""

from typing import Dict, Any, List
import flet as ft
from ui.theme import (
    BG_SURFACE,
    BORDER_COLOR,
    PRIMARY,
    ACCENT_CYAN,
    SUCCESS_GREEN,
    WARNING_AMBER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
)


class FinancialsTab(ft.Container):
    """Financials view presenting key ratios, valuation, cash position, and quarterly data."""

    def __init__(self, data: Dict[str, Any]):
        super().__init__()
        self.data = data
        self.build_ui()

    def update_data(self, data: Dict[str, Any]):
        self.data = data
        self.build_ui()
        self.update()

    def _build_metric_card(self, title: str, value: str, subtext: str, icon: str, value_color: str = TEXT_PRIMARY) -> ft.Container:
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(title, size=11, weight=ft.FontWeight.W_600, color=TEXT_MUTED),
                    ft.Icon(icon, size=14, color=ACCENT_CYAN),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text(value, size=18, weight=ft.FontWeight.BOLD, color=value_color),
                ft.Text(subtext, size=11, color=TEXT_SECONDARY),
            ], spacing=3),
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
        f = self.data.get("financials", {})

        # Grid of 15 Financial Metrics across 3 functional groups:
        # Group 1: Valuation & Market
        # Group 2: Profitability & Cash Flow
        # Group 3: Balance Sheet & Growth

        grid_row1 = ft.Row([
            self._build_metric_card("CURRENT PRICE", f.get("current_price", "$233.95"), "Real-time quote", ft.Icons.ATTACH_MONEY),
            self._build_metric_card("MARKET CAP", f.get("market_cap", "$5.65T"), "Total enterprise equity", ft.Icons.PUBLIC),
            self._build_metric_card("P/E RATIO (TTM)", f.get("pe_ratio", "29.58x"), "Price to earnings", ft.Icons.ANALYTICS_OUTLINED),
            self._build_metric_card("P/S RATIO (TTM)", f.get("ps_ratio", "18.65x"), "Price to sales", ft.Icons.PIE_CHART_OUTLINED),
            self._build_metric_card("EV/EBITDA", f.get("ev_ebitda", "27.90x"), "Enterprise valuation multiple", ft.Icons.INSIGHTS),
        ], spacing=10, wrap=True)

        grid_row2 = ft.Row([
            self._build_metric_card("REVENUE (TTM)", f.get("revenue_ttm", "$302.97B"), "Trailing 12-month sales", ft.Icons.TRENDING_UP, SUCCESS_GREEN),
            self._build_metric_card("NET INCOME (TTM)", f.get("net_income_ttm", "$192.88B"), "Trailing 12-month profit", ft.Icons.ACCOUNT_BALANCE_WALLET, SUCCESS_GREEN),
            self._build_metric_card("DILUTED EPS", f.get("diluted_eps", "$7.91"), "Earnings per share", ft.Icons.MONETIZATION_ON_OUTLINED),
            self._build_metric_card("GROSS MARGIN", f.get("gross_margin", "74.67%"), "Gross profit efficiency", ft.Icons.PERCENT, SUCCESS_GREEN),
            self._build_metric_card("OPERATING MARGIN", f.get("operating_margin", "66.24%"), "Operating margin leverage", ft.Icons.SHUFFLE, SUCCESS_GREEN),
        ], spacing=10, wrap=True)

        grid_row3 = ft.Row([
            self._build_metric_card("FREE CASH FLOW", f.get("free_cash_flow", "$41.81B"), "FCF generation (TTM)", ft.Icons.PAYMENTS_OUTLINED, SUCCESS_GREEN),
            self._build_metric_card("TOTAL CASH & EQUIV", f.get("total_cash", "$62.47B"), "Liquid reserves", ft.Icons.SAVINGS_OUTLINED),
            self._build_metric_card("TOTAL DEBT", f.get("total_debt", "$38.86B"), "Long & short term debt", ft.Icons.CREDIT_CARD_OUTLINED),
            self._build_metric_card("REVENUE GROWTH", f.get("revenue_growth", "+105.90%"), "Year-over-year expansion", ft.Icons.AUTO_GRAPH, SUCCESS_GREEN),
            self._build_metric_card("EPS GROWTH", f.get("eps_growth", "+127.80%"), "Year-over-year EPS acceleration", ft.Icons.EXPAND_LESS, SUCCESS_GREEN),
        ], spacing=10, wrap=True)

        # Historical Quarters Table
        history = f.get("historical_quarters", [])
        table_rows = []
        for item in history:
            table_rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(item.get("quarter", "-"), weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY)),
                        ft.DataCell(ft.Text(item.get("revenue", "-"), color=TEXT_PRIMARY)),
                        ft.DataCell(ft.Text(item.get("net_income", "-"), color=SUCCESS_GREEN, weight=ft.FontWeight.W_600)),
                        ft.DataCell(ft.Text(item.get("gross_margin", "-"), color=ACCENT_CYAN)),
                        ft.DataCell(ft.Text(item.get("fcf", "-"), color=TEXT_PRIMARY)),
                    ]
                )
            )

        data_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Fiscal Quarter", weight=ft.FontWeight.BOLD, color=TEXT_MUTED)),
                ft.DataColumn(ft.Text("Revenue", weight=ft.FontWeight.BOLD, color=TEXT_MUTED)),
                ft.DataColumn(ft.Text("Net Income", weight=ft.FontWeight.BOLD, color=TEXT_MUTED)),
                ft.DataColumn(ft.Text("Gross Margin", weight=ft.FontWeight.BOLD, color=TEXT_MUTED)),
                ft.DataColumn(ft.Text("Free Cash Flow", weight=ft.FontWeight.BOLD, color=TEXT_MUTED)),
            ],
            rows=table_rows,
            heading_row_color="#131B2E",
            border=ft.Border(
                top=ft.BorderSide(1, BORDER_COLOR),
                bottom=ft.BorderSide(1, BORDER_COLOR),
                left=ft.BorderSide(1, BORDER_COLOR),
                right=ft.BorderSide(1, BORDER_COLOR),
            ),
            border_radius=8,
            horizontal_margin=16,
            column_spacing=24,
        )

        table_card = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.CALENDAR_MONTH_OUTLINED, size=18, color=PRIMARY),
                    ft.Text("Quarterly Financial Performance Track Record", size=14, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                ], spacing=8),
                ft.Row([data_table], scroll=ft.ScrollMode.AUTO),
            ], spacing=10),
            bgcolor=BG_SURFACE,
            border_radius=10,
            padding=16,
            border=ft.Border(
                top=ft.BorderSide(1, BORDER_COLOR),
                bottom=ft.BorderSide(1, BORDER_COLOR),
                left=ft.BorderSide(1, BORDER_COLOR),
                right=ft.BorderSide(1, BORDER_COLOR),
            ),
        )

        self.content = ft.Column([
            grid_row1,
            grid_row2,
            grid_row3,
            table_card,
        ], spacing=12)
