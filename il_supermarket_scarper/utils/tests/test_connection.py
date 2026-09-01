"""Unit tests for download helpers."""

import asyncio
from unittest.mock import patch

from il_supermarket_scarper.utils.connection import (
    url_retrieve_to_memory,
    wget_file_to_memory,
)


class _FakeResponse:
    """Minimal requests response for url_retrieve_to_memory."""

    def __init__(self, body=b"data"):
        self.headers = {"Content-Length": str(len(body))}
        self._body = body

    def raise_for_status(self):
        """No-op success."""

    def iter_content(self, chunk_size=8192):  # pylint: disable=unused-argument
        """Yield the body once."""
        yield self._body

    def close(self):
        """No-op close for contextlib.closing."""


def test_url_retrieve_unescapes_html_entities_and_sends_user_agent():
    """Azure SAS links in HTML use &amp;; requests must see a decoded URL."""
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs.get("headers")
        return _FakeResponse(b"gzxx")

    with patch("il_supermarket_scarper.utils.connection.requests.get", fake_get):
        body = url_retrieve_to_memory(
            "https://blob.example/promo/file.gz?sv=2014-02-14&amp;sr=b&amp;sp=r"
        )

    assert body == b"gzxx"
    assert (
        captured["url"] == "https://blob.example/promo/file.gz?sv=2014-02-14&sr=b&sp=r"
    )
    assert "User-Agent" in captured["headers"]


def test_wget_missing_does_not_shell_out():
    """Daily-publish images have no wget; fallback must fail closed, not /bin/sh."""

    async def run():
        with patch(
            "il_supermarket_scarper.utils.connection.shutil.which", return_value=None
        ), patch(
            "il_supermarket_scarper.utils.connection.asyncio.create_subprocess_shell"
        ) as subprocess_shell:
            try:
                await wget_file_to_memory("https://example.com/file.gz")
            except FileNotFoundError as exc:
                assert "wget is not installed" in str(exc)
            else:
                raise AssertionError("expected FileNotFoundError")
            subprocess_shell.assert_not_called()

    asyncio.run(run())
