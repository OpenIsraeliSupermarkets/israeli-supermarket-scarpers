"""Live: a Shufersal file is not downloaded again after its link signature rotates.

Shufersal links are Azure blob URLs signed with a SAS token (``sig``/``se``)
that the site rotates about every 5 minutes (#233). Run 1 downloads one store
file. Later runs share the same status DB and are pinned to that file name;
they must download nothing, including the run that sees a new signature.
"""

import asyncio
import os
import re
import tempfile
import time
import unittest
from urllib.parse import parse_qs, urlsplit

from il_supermarket_scarper.scrappers.shufersal import Shufersal
from il_supermarket_scarper.utils import DiskFileOutput, FileTypesFilters

# The signature rotates about every 5 minutes; allow some slack.
MAX_WAIT_SECONDS = 8 * 60
POLL_SECONDS = 60


def _sig(url):
    return parse_qs(urlsplit(url or "").query).get("sig", [None])[0]


class TestShufersalSignedRerun(unittest.IsolatedAsyncioTestCase):
    """Re-runs after the SAS signature changes must skip the verified file."""

    async def _run(self, dump_path, **kwargs):
        """One scrape with a fresh scraper (as a new run), sharing ``dump_path``.

        Returns (results, links seen on the site per file name).
        """
        # The JSON status DB lives next to the storage folder, so keep both
        # inside ``dump_path`` (a bare temp dir would share /tmp/status).
        storage = os.path.join(dump_path, "Shufersal")
        scraper = Shufersal(file_output=DiskFileOutput(storage_path=storage))
        seen = {}
        original = scraper.unique_listings

        async def record_listed(state, iterable):
            # Every listing passes through here before the verified-skip
            # filter, so this sees the link (and its signature) of this run.
            async def tap():
                async for entry in iterable:
                    seen[entry.name] = entry.url
                    yield entry

            async for entry in original(state, tap()):
                yield entry

        scraper.unique_listings = record_listed
        results = [
            result
            async for result in scraper.scrape(
                files_types=FileTypesFilters.only_store(), **kwargs
            )
        ]
        return results, seen

    async def test_rotated_signature_does_not_redownload(self):
        """Run 1 downloads; runs after the signature rotates download nothing."""
        with tempfile.TemporaryDirectory() as dump_path:
            first, _ = await self._run(dump_path, limit=1)
            downloaded = [r for r in first if r.downloaded]
            self.assertEqual(len(downloaded), 1, "run 1 should download one file")
            name = downloaded[0].file_entry.name
            first_sig = _sig(downloaded[0].file_entry.url)
            self.assertIsNotNone(first_sig, "Shufersal links should be SAS-signed")

            pinned = f"^{re.escape(name)}$"
            deadline = time.monotonic() + MAX_WAIT_SECONDS
            while True:
                results, seen = await self._run(dump_path, file_name_regex=pinned)
                self.assertIn(name, seen, "the file should still be listed")
                self.assertEqual(
                    [r.file_entry.name for r in results if r.downloaded],
                    [],
                    "a verified file must not be downloaded again",
                )
                if _sig(seen[name]) != first_sig:
                    return  # signature rotated and the file was still skipped
                if time.monotonic() > deadline:
                    self.skipTest(
                        f"signature did not rotate within {MAX_WAIT_SECONDS}s; "
                        "rotation case not exercised"
                    )
                await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    unittest.main()
