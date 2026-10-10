"""
Unit Tests for SearXNG MCP Server and Client
Verifies:
- MCP server tool registration
- SearXNGClient health check logic
- Direct HTTP fallback execution
- Web page reading and cleaning
"""

import unittest
import asyncio
from unittest.mock import patch, MagicMock
from tools.mcp.searxng_client import SearXNGClient
from tools.mcp.searxng_server import server, execute_read_page


class TestSearXNGMCP(unittest.TestCase):
    """Test suite for local-first SearXNG MCP integration."""

    def setUp(self):
        self.client = SearXNGClient(searxng_url="http://127.0.0.1:9999")

    def test_mcp_server_tools_registered(self):
        """Verifies that MCP server exposes searxng_search and read_web_page tools."""
        # Check tool names on server
        tools = asyncio.run(server.list_tools())
        tool_names = [t.name for t in tools]
        self.assertIn("searxng_search", tool_names)
        self.assertIn("read_web_page", tool_names)

    def test_health_check_offline_returns_fallback_mode(self):
        """When SearXNG is unreachable, health check must gracefully report fallback mode."""
        health = self.client.check_health()
        self.assertIn("status", health)
        self.assertEqual(health["tool"], "searxng_mcp")
        self.assertEqual(health["active_mode"], "direct_http_fallback")
        self.assertEqual(health["status"], "unavailable")

    @patch("tools.mcp.searxng_client.httpx.Client")
    def test_health_check_online_returns_available(self, mock_client_cls):
        """When SearXNG responds with JSON results, health check reports available."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "application/json"}
        mock_resp.json.return_value = {"results": [{"title": "Test"}]}

        mock_instance = MagicMock()
        mock_instance.__enter__.return_value.get.return_value = mock_resp
        mock_client_cls.return_value = mock_instance

        health = self.client.check_health()
        self.assertEqual(health["status"], "available")
        self.assertEqual(health["active_mode"], "searxng_mcp")

    def test_read_page_cleaning(self):
        """Verifies HTML cleaning strips scripts and styles and extracts text."""
        sample_html = """
        <html>
            <head><title>Test Article</title><style>.hidden { display: none; }</style></head>
            <body>
                <header>Navigation</header>
                <script>console.log("ad code");</script>
                <main>
                    <h1>Quarterly Revenue Record</h1>
                    <p>Company posted $30B in revenue for the fiscal quarter.</p>
                </main>
                <footer>Copyright 2026</footer>
            </body>
        </html>
        """
        from unittest.mock import AsyncMock
        with patch("tools.mcp.searxng_server.httpx.AsyncClient") as mock_client:
            mock_resp = MagicMock()
            mock_resp.text = sample_html
            mock_resp.status_code = 200
            mock_instance = MagicMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.get = AsyncMock(return_value=mock_resp)
            mock_client.return_value = mock_instance

            res = asyncio.run(execute_read_page("http://example.com/article"))
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["title"], "Test Article")
            self.assertIn("Quarterly Revenue Record", res["content"])
            self.assertNotIn("console.log", res["content"])
            self.assertNotIn("Copyright 2026", res["content"])

    def test_search_fallback_on_searxng_error(self):
        """Verifies that search falls back to direct HTTP when SearXNG errors."""
        # SearXNG on 9999 is offline, search should return direct_http_fallback without crashing
        res = self.client.search_sync("NVIDIA earnings 2026", max_results=2)
        self.assertIn("status", res)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["source"], "direct_http_fallback")
        self.assertGreaterEqual(len(res["results"]), 1)


if __name__ == "__main__":
    unittest.main()
