"""A file the FTP server says is gone (550) must fail at once, not after ~8.5 min.

Regression for #215: Cerberus listings can go stale overnight; every listed
file then answered ``550 File not found`` and was retried 8 times with
exponential backoff, which pushed a prod scrape past its 330-minute timeout.
"""

import asyncio
import socket
from ftplib import error_perm
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import requests

from il_supermarket_scarper.utils.network.connection import (
    FtpFileMissingError,
    fetch_file_from_ftp_to_memory,
)

CONN = "il_supermarket_scarper.utils.network.connection"


def _fetch():
    return asyncio.run(
        fetch_file_from_ftp_to_memory(
            "ftp.example", "user", "", "/", "Promo123-001-001-20261102-180000.gz", 30
        )
    )


def test_missing_file_550_fails_after_one_attempt_without_sleeping():
    """550 is permanent: one attempt, no backoff sleep, clear error."""
    download = MagicMock(side_effect=error_perm("550 File not found"))
    sleep = AsyncMock()
    with patch(f"{CONN}._sync_ftp_download_to_memory", download), patch(
        f"{CONN}.asyncio.sleep", sleep
    ):
        with pytest.raises(FtpFileMissingError) as raised:
            _fetch()

    assert download.call_count == 1
    sleep.assert_not_awaited()
    assert "550" in str(raised.value)
    assert isinstance(raised.value.__cause__, error_perm)


def test_transient_ftp_error_is_still_retried():
    """A timeout followed by success still returns the data."""
    download = MagicMock(side_effect=[socket.timeout("timed out"), b"payload"])
    sleep = AsyncMock()
    with patch(f"{CONN}._sync_ftp_download_to_memory", download), patch(
        f"{CONN}.asyncio.sleep", sleep
    ):
        assert _fetch() == b"payload"

    assert download.call_count == 2
    sleep.assert_awaited_once()


def test_other_permanent_ftp_replies_keep_retrying():
    """Only 550 short-circuits; e.g. a 530 under load keeps today's retries."""
    download = MagicMock(side_effect=error_perm("530 Login incorrect."))
    sleep = AsyncMock()
    with patch(f"{CONN}._sync_ftp_download_to_memory", download), patch(
        f"{CONN}.asyncio.sleep", sleep
    ):
        with pytest.raises(error_perm):
            _fetch()

    assert download.call_count == 8


def test_http_404_is_not_retried():
    """HTTP engines must keep failing fast on a missing blob (Shufersal 404s)."""
    # pylint: disable=import-outside-toplevel
    from il_supermarket_scarper.engines.engine import Engine

    response = MagicMock(status_code=404)
    error = requests.HTTPError(
        "404 Client Error: blob does not exist", response=response
    )
    retrieve = MagicMock(side_effect=error)
    sleep = AsyncMock()

    with patch(
        "il_supermarket_scarper.engines.engine.url_retrieve_to_memory", retrieve
    ), patch(f"{CONN}.asyncio.sleep", sleep):
        with pytest.raises(requests.HTTPError):
            asyncio.run(
                # self is unused by retrieve_file_to_memory
                Engine.retrieve_file_to_memory(
                    None, "https://blob.example/promo/file.gz"
                )
            )

    assert retrieve.call_count == 1
    sleep.assert_not_awaited()
