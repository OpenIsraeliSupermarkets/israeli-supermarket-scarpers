"""Regression test: a persistently corrupt FTP file yields a clean failed result."""

import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from il_supermarket_scarper.engines.cerberus import Cerberus
from il_supermarket_scarper.utils import (
    DiskFileOutput,
    DumpFolderNames,
    FileEntry,
    ScrapingResult,
)
from il_supermarket_scarper.utils.network.connection import FtpFileMissingError


class TestCerberusCorruptSource(unittest.IsolatedAsyncioTestCase):
    """persist_from_ftp must not raise when extraction fails every attempt."""

    async def test_truncated_gzip_yields_source_corrupt(self):
        """3 failed extractions -> one failed result flagged source_corrupt."""
        entry = FileEntry(
            name="PriceFull7290492000005-001-512-20261003-000505.gz",
            url="",
            size=1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            engine = Cerberus(
                chain=DumpFolderNames.DOR_ALON,
                chain_id="7290492000005",
                file_output=DiskFileOutput(storage_path=tmp),
            )
            failed = ScrapingResult(
                file_entry=entry,
                downloaded=True,
                save_decision=None,
                extract_succefully=False,
                error="gzip truncated",
            )
            fetch = AsyncMock(return_value=b"truncated")
            finalize = AsyncMock(return_value=failed)
            with patch(
                "il_supermarket_scarper.engines.cerberus."
                "fetch_file_from_ftp_to_memory",
                fetch,
            ), patch.object(engine, "_finalize_extracted_content", finalize):
                results = [r async for r in engine.persist_from_ftp(entry)]

        self.assertEqual(fetch.await_count, 3)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].source_corrupt)
        self.assertFalse(results[0].extract_succefully)
        self.assertIn("source corrupt after 3 downloads", results[0].error)

    async def test_missing_remote_file_is_not_flagged_for_restart(self):
        """A 550 (file gone) yields one failed result without restart_and_retry."""
        entry = FileEntry(
            name="PromoFull7290058140886-001-721-20261102-180031.gz",
            url="",
            size=1,
        )
        with tempfile.TemporaryDirectory() as tmp:
            engine = Cerberus(
                chain=DumpFolderNames.RAMI_LEVY,
                chain_id="7290058140886",
                file_output=DiskFileOutput(storage_path=tmp),
            )
            fetch = AsyncMock(
                side_effect=FtpFileMissingError(
                    "remote file missing (550): " + entry.name
                )
            )
            with patch(
                "il_supermarket_scarper.engines.cerberus."
                "fetch_file_from_ftp_to_memory",
                fetch,
            ):
                results = [r async for r in engine.persist_from_ftp(entry)]

        self.assertEqual(fetch.await_count, 1)
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].restart_and_retry)
        self.assertFalse(results[0].downloaded)
        self.assertIn("550", results[0].error)
