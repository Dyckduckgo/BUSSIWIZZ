import os
import sys
import argparse
import asyncio
from typing import Optional, Dict, Any, List

try:
    import flet as ft
except ImportError:
    from env_bootstrap import bootstrap_environment
    bootstrap_environment(["flet", "requests", "dotenv"])
    import flet as ft

from services.research_service import ResearchService
from financial_data import format_currency, format_percent, format_ratio


def launch_ui(
    host: Optional[str] = None,
    port: Optional[int] = None,
    web: bool = False,
):
    """Starts the Flet user interface application with configurable host, port, and view."""
    from env_bootstrap import find_available_port

    target_host = host or os.getenv("HOST", "127.0.0.1")
    env_port = os.getenv("PORT")
    target_port = port if port is not None else (int(env_port) if env_port else 8550)

    is_headless = sys.platform != "win32" and not (os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))
    web_mode = web or bool(os.getenv("WEB_MODE")) or is_headless

    if web_mode:
        resolved_port = find_available_port(target_port, host=target_host)
        if resolved_port != target_port:
            print(f"[Bussiwzz] Port {target_port} was busy. Using available port {resolved_port}.")
        target_port = resolved_port
        print(f"[Bussiwzz] Serving research UI at: http://{target_host}:{target_port}")
        ft.run(
            main,
            host=target_host,
            port=target_port,
            view=ft.AppView.WEB_BROWSER,
        )
    else:
        ft.run(
            main,
            view=ft.AppView.FLET_APP,
        )


async def main(page: ft.Page):
    page.title = "Stock Research Agent - Free & Local-First"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    page.spacing = 15
    page.scroll = ft.ScrollMode.AUTO

    service = ResearchService()

    # Current research state
    current_data: Dict[str, Any] = {}
    active_tab = "report"

    # UI Controls: Search Row
    target_input = ft.TextField(
        label="Company Name or Stock Ticker",
        hint_text="e.g. NVDA, Apple, MSFT, Tesla",
        prefix_icon=ft.Icons.SEARCH,
        autofocus=True,
        expand=True,
    )
    papers_checkbox = ft.Checkbox(
        label="Include Academic Papers (OpenAlex)",
        value=False,
    )
    search_button = ft.FilledButton(
        content=ft.Row([ft.Icon(ft.Icons.ROCKET_LAUNCH), ft.Text("Research")]),
        height=50,
    )
    progress_bar = ft.ProgressBar(visible=False)
    status_text = ft.Text(value="", color=ft.Colors.GREY_400, size=13)

    # Health Check Container
    health_row = ft.Row(wrap=True, spacing=10)

    def update_health_indicators():
        statuses = service.get_health_status()
        health_row.controls.clear()

        # Tool mapping for friendly display
        tool_labels = {
            "searxng_mcp": ("SearXNG Web MCP", ft.Icons.TRAVEL_EXPLORE),
            "yfinance": ("yfinance Market Data", ft.Icons.SHOW_CHART),
            "sec_edgar": ("SEC EDGAR Filings", ft.Icons.ACCOUNT_BALANCE),
            "groq_llm": ("Groq LLM", ft.Icons.PSYCHOLOGY),
            "sqlite_db": ("SQLite Database", ft.Icons.STORAGE),
            "openalex_papers": ("OpenAlex Papers", ft.Icons.MENU_BOOK),
        }

        for key, (label, icon) in tool_labels.items():
            info = statuses.get(key, {})
            st = info.get("status", "unknown")
            mode = info.get("active_mode", "")
            msg = info.get("message", "")

            if st == "available":
                bg = ft.Colors.GREEN_900
                fg = ft.Colors.GREEN_200
                badge_text = "Ready" if mode != "direct_http_fallback" else "HTTP Fallback"
            elif st == "degraded" or mode == "direct_http_fallback":
                bg = ft.Colors.AMBER_900
                fg = ft.Colors.AMBER_200
                badge_text = "Fallback"
            else:
                bg = ft.Colors.RED_900 if key != "openalex_papers" else ft.Colors.GREY_800
                fg = ft.Colors.RED_200 if key != "openalex_papers" else ft.Colors.GREY_400
                badge_text = "Offline"

            card = ft.Container(
                content=ft.Row([
                    ft.Icon(icon, size=16, color=fg),
                    ft.Text(f"{label}:", size=12, weight=ft.FontWeight.BOLD),
                    ft.Text(badge_text, size=12, color=fg),
                ], alignment=ft.MainAxisAlignment.START, spacing=6),
                bgcolor=bg,
                padding=ft.Padding(8, 4, 8, 4),
                border_radius=12,
                tooltip=msg,
            )
            health_row.controls.append(card)

    update_health_indicators()

    # Fallback banner
    fallback_banner = ft.Container(visible=False, bgcolor=ft.Colors.AMBER_950, padding=12, border_radius=8)

    # Navigation Segments
    view_selector = ft.SegmentedButton(
        segments=[
            ft.Segment(value="report", label=ft.Text("Research Report"), icon=ft.Icon(ft.Icons.DESCRIPTION)),
            ft.Segment(value="financials", label=ft.Text("Financial Metrics"), icon=ft.Icon(ft.Icons.TABLE_CHART)),
            ft.Segment(value="sec", label=ft.Text("SEC Filings & Facts"), icon=ft.Icon(ft.Icons.ACCOUNT_BALANCE)),
            ft.Segment(value="web", label=ft.Text("Web Sources"), icon=ft.Icon(ft.Icons.PUBLIC)),
            ft.Segment(value="history", label=ft.Text("Past Sessions"), icon=ft.Icon(ft.Icons.HISTORY)),
        ],
        selected={"report"},
    )

    # Content Container
    content_area = ft.Container(expand=True, padding=10)

    def render_active_view():
        nonlocal active_tab
        if not current_data and active_tab != "history":
            content_area.content = ft.Container(
                content=ft.Column([
                    ft.Icon(ft.Icons.ANALYTICS_OUTLINED, size=64, color=ft.Colors.GREY_600),
                    ft.Text("No active research session.", size=18, color=ft.Colors.GREY_400),
                    ft.Text("Enter a stock ticker or company name above and click Research.", size=14, color=ft.Colors.GREY_500),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                alignment=ft.Alignment.CENTER,
                padding=40,
            )
            page.update()
            return

        if active_tab == "report":
            report_md = current_data.get("full_report", "No report generated.")
            model_info = current_data.get("model_used", "N/A")
            content_area.content = ft.Column([
                ft.Row([
                    ft.Text(f"Synthesis Model: {model_info}", size=13, color=ft.Colors.BLUE_300, italic=True),
                ]),
                ft.Divider(),
                ft.Markdown(
                    value=report_md,
                    selectable=True,
                    extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                ),
            ], scroll=ft.ScrollMode.AUTO)

        elif active_tab == "financials":
            metrics = current_data.get("financial_metrics")
            if not metrics:
                content_area.content = ft.Text("No financial data available for this company.", color=ft.Colors.GREY_400)
            else:
                summary = metrics.to_summary_dict()
                rows = []
                for k, v in summary.items():
                    rows.append(
                        ft.DataRow(cells=[
                            ft.DataCell(ft.Text(k, weight=ft.FontWeight.BOLD)),
                            ft.DataCell(ft.Text(str(v), color=ft.Colors.CYAN_200)),
                        ])
                    )
                table = ft.DataTable(
                    columns=[
                        ft.DataColumn(ft.Text("Metric", weight=ft.FontWeight.BOLD)),
                        ft.DataColumn(ft.Text("Calculated Value", weight=ft.FontWeight.BOLD)),
                    ],
                    rows=rows,
                )
                content_area.content = ft.Column([
                    ft.Text(f"Financial Fundamentals for {metrics.company_name} ({metrics.symbol})", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text("Source: yfinance & Python Derived Calculations (Zero paid API keys)", size=12, color=ft.Colors.GREY_400),
                    ft.Divider(),
                    table,
                ], scroll=ft.ScrollMode.AUTO)

        elif active_tab == "sec":
            sec_report = current_data.get("sec_report")
            if not sec_report:
                content_area.content = ft.Text("No SEC EDGAR filings available (non-US public company or CIK not found).", color=ft.Colors.GREY_400)
            else:
                items = [
                    ft.Text(f"SEC EDGAR Regulatory Filings: {sec_report.company} (CIK: {sec_report.cik})", size=18, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                ]

                # Recent Filings
                if sec_report.filings:
                    items.append(ft.Text("Recent SEC Filings (10-K, 10-Q, 8-K, 20-F):", weight=ft.FontWeight.BOLD))
                    for form in ("10-K", "10-Q", "8-K", "20-F"):
                        for f in sec_report.filings.get(form, [])[:2]:
                            items.append(
                                ft.Card(
                                    content=ft.Container(
                                        content=ft.Column([
                                            ft.Row([
                                                ft.Text(f"Form {f.form}", weight=ft.FontWeight.BOLD, color=ft.Colors.LIGHT_BLUE_200),
                                                ft.Text(f"Filed: {f.filing_date}", size=12, color=ft.Colors.GREY_400),
                                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                            ft.Text(f"Accession: {f.accession_number}", size=11, color=ft.Colors.GREY_500),
                                            ft.Text(f"URL: {f.source_url}", size=12, color=ft.Colors.BLUE_300, selectable=True),
                                        ], spacing=4),
                                        padding=10,
                                    )
                                )
                            )

                # Form 4 Insider Transactions
                if sec_report.insider_transactions:
                    items.append(ft.Divider())
                    items.append(ft.Text("Recent Form 4 Insider Activity:", weight=ft.FontWeight.BOLD))
                    for trade in sec_report.insider_transactions[:4]:
                        items.append(
                            ft.Text(f"• {trade.reporting_owner}: {trade.transaction_type} {trade.shares:,.0f} shares ({trade.transaction_date})", size=13)
                        )

                # XBRL GAAP Facts
                if sec_report.facts:
                    items.append(ft.Divider())
                    items.append(ft.Text("Extracted XBRL GAAP Facts:", weight=ft.FontWeight.BOLD))
                    for fact in sec_report.facts[:8]:
                        items.append(
                            ft.Text(f"• {fact.claim}: {fact.value or 'Disclosed'} (Form {fact.filing_type} - {fact.filing_date})", size=13)
                        )

                content_area.content = ft.Column(items, scroll=ft.ScrollMode.AUTO)

        elif active_tab == "web":
            sources = current_data.get("sources", [])
            mode = current_data.get("web_source_mode", "web")
            items = [
                ft.Text(f"Web News & Search Results (Active Engine: {mode})", size=18, weight=ft.FontWeight.BOLD),
                ft.Divider(),
            ]
            if not sources:
                items.append(ft.Text("No web sources recorded.", color=ft.Colors.GREY_400))
            else:
                for s in sources:
                    items.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column([
                                    ft.Text(s.get("title", "No Title"), weight=ft.FontWeight.BOLD),
                                    ft.Text(s.get("snippet", ""), size=12, color=ft.Colors.GREY_400),
                                    ft.Text(s.get("url", ""), size=11, color=ft.Colors.BLUE_300, selectable=True),
                                ], spacing=4),
                                padding=12,
                            )
                        )
                    )
            content_area.content = ft.Column(items, scroll=ft.ScrollMode.AUTO)

        elif active_tab == "history":
            recent = service.get_recent_history(limit=15)
            items = [
                ft.Text("Recent SQLite Research Sessions", size=18, weight=ft.FontWeight.BOLD),
                ft.Divider(),
            ]
            if not recent:
                items.append(ft.Text("No past sessions found in SQLite database.", color=ft.Colors.GREY_400))
            else:
                for r in recent:
                    def make_load_handler(sid):
                        async def load_handler(e):
                            detail = service.get_session_by_id(sid)
                            if detail:
                                nonlocal current_data, active_tab
                                current_data = {
                                    "company": detail.get("company"),
                                    "ticker": detail.get("ticker"),
                                    "model_used": detail.get("model_used"),
                                    "full_report": detail.get("full_report"),
                                    "sources": detail.get("web_sources", []),
                                }
                                active_tab = "report"
                                view_selector.selected = {"report"}
                                render_active_view()
                        return load_handler

                    items.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Row([
                                    ft.Column([
                                        ft.Text(f"{r.get('company')} ({r.get('ticker')})", weight=ft.FontWeight.BOLD),
                                        ft.Text(f"Date: {r.get('created_at')} | Status: {r.get('status')} | Model: {r.get('model_used')}", size=11, color=ft.Colors.GREY_400),
                                    ], expand=True),
                                    ft.FilledButton("Load", on_click=make_load_handler(r.get("session_id"))),
                                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                                padding=10,
                            )
                        )
                    )
            content_area.content = ft.Column(items, scroll=ft.ScrollMode.AUTO)

        page.update()

    def on_view_change(e):
        nonlocal active_tab
        selected_set = e.control.selected
        if selected_set:
            active_tab = list(selected_set)[0]
            render_active_view()

    view_selector.on_change = on_view_change

    async def execute_search_action(e):
        target = target_input.value.strip()
        if not target:
            target_input.error_text = "Please enter a stock ticker or company name"
            page.update()
            return

        target_input.error_text = None
        search_button.disabled = True
        progress_bar.visible = True
        status_text.value = f"Researching '{target}' across yfinance, SEC EDGAR, and web..."
        fallback_banner.visible = False
        page.update()

        try:
            res = await service.execute_research(
                company_or_ticker=target,
                include_papers=papers_checkbox.value,
            )
            nonlocal current_data, active_tab
            current_data = res
            active_tab = "report"
            view_selector.selected = {"report"}

            # Display any fallbacks
            fallbacks = res.get("fallbacks_used", [])
            if fallbacks:
                fallback_banner.content = ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINE, color=ft.Colors.AMBER_400),
                        ft.Text("Fallback Notices:", weight=ft.FontWeight.BOLD, color=ft.Colors.AMBER_200),
                    ]),
                    *[ft.Text(f"• {f}", size=12, color=ft.Colors.AMBER_100) for f in fallbacks],
                ], spacing=4)
                fallback_banner.visible = True

            status_text.value = f"Research complete for {res.get('company')} ({res.get('ticker')})!"
            update_health_indicators()
            render_active_view()

        except Exception as exc:
            status_text.value = f"Error during research: {str(exc)}"
        finally:
            search_button.disabled = False
            progress_bar.visible = False
            page.update()

    search_button.on_click = execute_search_action
    target_input.on_submit = execute_search_action

    # Build Page Layout
    page.add(
        ft.Row([
            ft.Icon(ft.Icons.SHOW_CHART, size=32, color=ft.Colors.LIGHT_BLUE_400),
            ft.Column([
                ft.Text("Stock Research Agent", size=24, weight=ft.FontWeight.BOLD),
                ft.Text("Free & Local-First Architecture | Zero Paid Search / Zero Paid Financial APIs", size=12, color=ft.Colors.GREY_400),
            ], spacing=2),
        ], alignment=ft.MainAxisAlignment.START),
        ft.Divider(),
        health_row,
        ft.Row([target_input, search_button], alignment=ft.MainAxisAlignment.START),
        papers_checkbox,
        progress_bar,
        status_text,
        fallback_banner,
        ft.Divider(),
        view_selector,
        content_area,
    )

    render_active_view()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stock Research Agent (Flet)")
    parser.add_argument("--web", action="store_true", help="Launch in web browser mode")
    parser.add_argument("--host", type=str, default=None, help="Host address to bind (e.g. 127.0.0.1 or 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None, help="Port to bind in web mode (default: 8550 or $PORT)")
    args = parser.parse_args()

    launch_ui(host=args.host, port=args.port, web=args.web)
