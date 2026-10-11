import os
import sys
import argparse
from typing import Optional

# Safe fallback for windowed / GUI mode where sys.stdout and sys.stderr may be None
if sys.stdout is None:
    try:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass
if sys.stderr is None:
    try:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass

try:
    import flet as ft
except ImportError:
    from env_bootstrap import bootstrap_environment
    bootstrap_environment(["flet"])
    import flet as ft

from ui.theme import BG_DARK, BG_SURFACE, PRIMARY, SUCCESS_GREEN, TEXT_PRIMARY, WARNING_AMBER
from ui.mock_data import get_mock_research
from ui.components.sidebar import Sidebar
from ui.screens.dashboard import DashboardScreen
from ui.screens.settings_modal import create_settings_dialog
from services.research_service import ResearchService, ResearchResult
from config.app_config import (
    ensure_writable_dirs,
    get_assets_dir,
    get_reports_dir,
    APP_NAME,
)


def main(page: ft.Page):
    """Main application lifecycle initializing dark theme, sidebar, and dashboard."""
    page.title = APP_NAME
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG_DARK
    page.padding = 0
    page.spacing = 0

    # Ensure writable directories exist
    ensure_writable_dirs()

    # Configure application icon if available in assets
    assets_dir = get_assets_dir()
    icon_png = assets_dir / "icon.png"
    if icon_png.is_file():
        try:
            page.window.icon = str(icon_png)
        except Exception:
            pass

    # Backend Research Service (Flet UI calls ResearchService -> Orchestrator -> Agents)
    research_service = ResearchService()

    # Initial research state (fallback mock data until live run)
    state = {
        "ticker": "NVDA",
        "market": "NASDAQ",
        "data": get_mock_research("NVDA", "NASDAQ"),
    }

    # Asynchronous Research Flow (non-blocking task)
    async def execute_research_flow(ticker: str, market: str):
        target_ticker = ticker.strip().upper() if ticker.strip() else "NVDA"
        target_market = market.strip().upper() if market.strip() else "NASDAQ"

        # Update UI to researching state
        sidebar.set_loading(True)
        dashboard.set_status("In Progress")
        page.update()

        def on_stage_progress(stages_list: list):
            dashboard.update_progress(stages_list)
            page.update()

        try:
            # Delegate entire research run to ResearchService
            result: ResearchResult = await research_service.research_company(
                ticker=target_ticker,
                market=target_market,
                on_progress=on_stage_progress,
                timeout=120.0,
            )

            if result.status == "completed":
                state["ticker"] = result.ticker
                state["market"] = result.market
                state["data"] = result.to_dict()

                dashboard.update_data(state["data"])
                page.update()

                snack = ft.SnackBar(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=SUCCESS_GREEN, size=18),
                        ft.Text(
                            f"Research compiled successfully for {result.ticker} (Overall Score: {result.overall_score:.1f}/100)",
                            color=TEXT_PRIMARY,
                            weight=ft.FontWeight.W_600,
                        ),
                    ], spacing=8),
                    bgcolor="#064E3B",
                    duration=3500,
                )
                page.show_dialog(snack)

            elif result.status == "cancelled":
                dashboard.set_status("Cancelled")
                snack = ft.SnackBar(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CANCEL_OUTLINED, color="#F59E0B", size=18),
                        ft.Text(result.error_message or "Research was cancelled.", color=TEXT_PRIMARY),
                    ], spacing=8),
                    bgcolor="#451A03",
                    duration=3000,
                )
                page.show_dialog(snack)

            else:  # failed
                dashboard.set_status("Failed")
                snack = ft.SnackBar(
                    content=ft.Row([
                        ft.Icon(ft.Icons.ERROR_OUTLINE, color="#EF4444", size=18),
                        ft.Text(result.error_message or "Research run encountered an error.", color=TEXT_PRIMARY),
                    ], spacing=8),
                    bgcolor="#450A0A",
                    duration=5000,
                )
                page.show_dialog(snack)

        except Exception as err:
            dashboard.set_status("Failed")
            snack = ft.SnackBar(
                content=ft.Row([
                    ft.Icon(ft.Icons.ERROR_OUTLINE, color="#EF4444", size=18),
                    ft.Text(f"Unexpected research error: {str(err)}", color=TEXT_PRIMARY),
                ], spacing=8),
                bgcolor="#450A0A",
                duration=5000,
            )
            page.show_dialog(snack)

        finally:
            sidebar.set_loading(False)
            page.update()

    # Action Handlers
    def handle_research(ticker: str, market: str, recipient_email: str):
        page.run_task(execute_research_flow, ticker, market)

    def handle_cancel():
        target_ticker = sidebar.ticker_input.value.strip().upper()
        research_service.cancel_research(target_ticker)
        snack = ft.SnackBar(
            content=ft.Row([
                ft.Icon(ft.Icons.STOP_CIRCLE_OUTLINED, color="#F59E0B", size=18),
                ft.Text(f"Cancellation requested for {target_ticker}...", color=TEXT_PRIMARY),
            ], spacing=8),
            bgcolor="#451A03",
            duration=2000,
        )
        page.show_dialog(snack)

    def handle_settings():
        dlg = create_settings_dialog(page, on_save=lambda: page.show_dialog(
            ft.SnackBar(
                content=ft.Text("Preferences updated successfully.", color=TEXT_PRIMARY),
                bgcolor="#131B2E",
                duration=2000,
            )
        ))
        page.show_dialog(dlg)

    def handle_download_pdf():
        reports_dir = get_reports_dir()
        target_ticker = state.get("ticker", "RESEARCH").upper()
        report_file = reports_dir / f"{target_ticker}_Research_Report.md"
        report_data = state.get("data", {})
        report_text = report_data.get("full_report") or (
            f"# Institutional Research Dossier: {target_ticker}\n\n"
            f"Date: {report_data.get('research_date', 'Recent')}\n\n"
            f"Overall Institutional Score: {report_data.get('research_score', {}).get('total', 'N/A')}/100\n\n"
            f"Verdict: {report_data.get('score_details', {}).get('verdict', 'Neutral')}\n\n"
            f"Saved to: {report_file.as_posix()}\n"
        )
        report_file.write_text(report_text, encoding="utf-8")

        snack = ft.SnackBar(
            content=ft.Row([
                ft.Icon(ft.Icons.DESCRIPTION, color=PRIMARY, size=18),
                ft.Text(
                    f"Research Dossier exported: {report_file.name} to {reports_dir}",
                    color=TEXT_PRIMARY,
                ),
            ], spacing=8),
            bgcolor="#1E293B",
            duration=4000,
        )
        page.show_dialog(snack)

    def handle_send_email():
        email = sidebar.email_input.value.strip() or "analyst@firm.com"
        snack = ft.SnackBar(
            content=ft.Row([
                ft.Icon(ft.Icons.MARK_EMAIL_READ, color=SUCCESS_GREEN, size=18),
                ft.Text(f"Dossier PDF dispatched to {email} successfully.", color=TEXT_PRIMARY),
            ], spacing=8),
            bgcolor="#064E3B",
            duration=3500,
        )
        page.show_dialog(snack)

    def handle_load_session(ticker_symbol: str):
        sidebar.ticker_input.value = ticker_symbol
        sidebar.ticker_input.update()
        page.run_task(execute_research_flow, ticker_symbol, sidebar.market_input.value)

    # Initialize Sidebar and Dashboard Components
    sidebar = Sidebar(
        on_research=handle_research,
        on_settings=handle_settings,
        on_cancel=handle_cancel,
        width=290,
    )

    dashboard = DashboardScreen(
        data=state["data"],
        on_download_pdf=handle_download_pdf,
        on_send_email=handle_send_email,
        on_load_session=handle_load_session,
    )

    # Main Screen Layout (Sidebar on left, expanded Dashboard on right)
    layout = ft.Row(
        controls=[
            sidebar,
            dashboard,
        ],
        expand=True,
        spacing=0,
    )

    page.add(layout)


def launch_app(
    host: Optional[str] = None,
    port: Optional[int] = None,
    web: bool = False,
):
    """Launches the Flet equity research application with configurable port, host, and view."""
    # Ensure writable user directories on initial launch
    ensure_writable_dirs()

    # When launched via `flet run` CLI (which sets FLET_DISPLAY_URL_PREFIX and manages ports/views)
    is_flet_cli = bool(os.getenv("FLET_DISPLAY_URL_PREFIX") or os.getenv("FLET_SERVER_PORT"))
    if is_flet_cli:
        ft.run(main)
        return

    from env_bootstrap import find_available_port

    target_host = host or os.getenv("HOST", "127.0.0.1")
    env_port = os.getenv("PORT")
    target_port = port if port is not None else (int(env_port) if env_port else 8550)

    # Detect headless systems (e.g. Linux servers / containers without DISPLAY)
    is_headless = sys.platform != "win32" and not (os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))
    web_mode = web or bool(os.getenv("WEB_MODE")) or is_headless

    assets_dir_str = str(get_assets_dir())

    if web_mode:
        view = ft.AppView.WEB_BROWSER
        resolved_port = find_available_port(target_port, host=target_host)
        if resolved_port != target_port:
            print(f"[AI Stock Research] Port {target_port} was busy. Using available port {resolved_port}.")
        target_port = resolved_port
        print(f"[AI Stock Research] Serving web dashboard at: http://{target_host}:{target_port}")
        ft.run(
            main,
            host=target_host,
            port=target_port,
            view=view,
            assets_dir=assets_dir_str,
        )
    else:
        ft.run(
            main,
            view=ft.AppView.FLET_APP,
            assets_dir=assets_dir_str,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bussiwzz Equity Research Dashboard (Flet)")
    parser.add_argument("--web", action="store_true", help="Launch in web browser mode")
    parser.add_argument("--host", type=str, default=None, help="Host address to bind (e.g. 127.0.0.1 or 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None, help="Port to bind in web mode (default: 8550 or $PORT)")
    args = parser.parse_args()

    launch_app(host=args.host, port=args.port, web=args.web)
