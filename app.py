import os
import sys
import argparse
from typing import Optional

try:
    import flet as ft
except ImportError:
    from env_bootstrap import bootstrap_environment
    bootstrap_environment(["flet"])
    import flet as ft

from ui.theme import BG_DARK, BG_SURFACE, PRIMARY, SUCCESS_GREEN, TEXT_PRIMARY
from ui.mock_data import get_mock_research
from ui.components.sidebar import Sidebar
from ui.screens.dashboard import DashboardScreen
from ui.screens.settings_modal import create_settings_dialog


def main(page: ft.Page):
    """Main application lifecycle initializing dark theme, sidebar, and dashboard."""
    page.title = "Bussiwzz - AI Stock Research"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = BG_DARK
    page.padding = 0
    page.spacing = 0

    # Current research state
    state = {
        "ticker": "NVDA",
        "market": "NASDAQ",
        "data": get_mock_research("NVDA", "NASDAQ"),
    }

    # Action Handlers
    def handle_research(ticker: str, market: str, recipient_email: str):
        target_ticker = ticker.strip().upper() if ticker.strip() else "NVDA"
        target_market = market.strip().upper() if market.strip() else "NASDAQ"

        state["ticker"] = target_ticker
        state["market"] = target_market
        state["data"] = get_mock_research(target_ticker, target_market)

        dashboard.update_data(state["data"])
        page.update()

        # Toast notification
        snack = ft.SnackBar(
            content=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE, color=SUCCESS_GREEN, size=18),
                ft.Text(f"Research compiled successfully for {target_ticker} ({target_market})", color=TEXT_PRIMARY, weight=ft.FontWeight.W_600),
            ], spacing=8),
            bgcolor="#064E3B",
            duration=3000,
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
        snack = ft.SnackBar(
            content=ft.Row([
                ft.Icon(ft.Icons.PICTURE_AS_PDF, color=PRIMARY, size=18),
                ft.Text(
                    f"Research Dossier exported: reports/{state['ticker']}_Research_Report.pdf",
                    color=TEXT_PRIMARY,
                ),
            ], spacing=8),
            bgcolor="#1E293B",
            duration=3500,
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
        handle_research(ticker_symbol, sidebar.market_input.value, sidebar.email_input.value)

    # Initialize Sidebar and Dashboard Components
    sidebar = Sidebar(
        on_research=handle_research,
        on_settings=handle_settings,
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
    from env_bootstrap import find_available_port

    target_host = host or os.getenv("HOST", "127.0.0.1")
    env_port = os.getenv("PORT")
    target_port = port if port is not None else (int(env_port) if env_port else 8550)

    # Detect headless systems (e.g. Linux servers / containers without DISPLAY)
    is_headless = sys.platform != "win32" and not (os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY"))
    web_mode = web or bool(os.getenv("WEB_MODE")) or is_headless

    if web_mode:
        view = ft.AppView.WEB_BROWSER
        resolved_port = find_available_port(target_port, host=target_host)
        if resolved_port != target_port:
            print(f"[Bussiwzz] Port {target_port} was busy. Using available port {resolved_port}.")
        target_port = resolved_port
        print(f"[Bussiwzz] Serving web dashboard at: http://{target_host}:{target_port}")
        ft.run(
            main,
            host=target_host,
            port=target_port,
            view=view,
        )
    else:
        ft.run(
            main,
            view=ft.AppView.FLET_APP,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bussiwzz Equity Research Dashboard (Flet)")
    parser.add_argument("--web", action="store_true", help="Launch in web browser mode")
    parser.add_argument("--host", type=str, default=None, help="Host address to bind (e.g. 127.0.0.1 or 0.0.0.0)")
    parser.add_argument("--port", type=int, default=None, help="Port to bind in web mode (default: 8550 or $PORT)")
    args = parser.parse_args()

    launch_app(host=args.host, port=args.port, web=args.web)
