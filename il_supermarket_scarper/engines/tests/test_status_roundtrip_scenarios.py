"""What every engine writes during ``scrape()`` must load as the status contract."""

import tempfile
import unittest

from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils.scraping.scraper_status_contract import (
    DownloadedStatus,
    FailedStatus,
)

from .status_roundtrip.cases import ENGINE_CASES
from .status_roundtrip.runner import RoundtripRunner


class TestStatusRoundtripScenarios(unittest.IsolatedAsyncioTestCase):
    """Offline scenarios, run once per engine class."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(self._tmp.cleanup)

    async def _run(self, case, **scenario):
        """Run one case through a scenario and load its status."""
        return await RoundtripRunner(case, self._tmp.name).run(**scenario)

    @staticmethod
    def _downloaded(status):
        """The ``downloaded`` events of a loaded status."""
        return [e for e in status.events if isinstance(e, DownloadedStatus)]

    async def test_success(self):
        """Listed files download and the status loads."""
        for case in ENGINE_CASES:
            with self.subTest(engine=case.engine_cls.__name__):
                status = await self._run(case)
                self.assertTrue(status.validate_file_status())
                downloaded = self._downloaded(status)
                self.assertGreaterEqual(len(downloaded), 1)
                self.assertTrue(all(e.downloaded_successfully for e in downloaded))

    async def test_download_error(self):
        """A swallowed download error is recorded and loads."""
        for case in ENGINE_CASES:
            with self.subTest(engine=case.engine_cls.__name__):
                status = await self._run(case, download_error=True)
                self.assertTrue(status.validate_file_status())
                downloaded = self._downloaded(status)
                self.assertGreaterEqual(len(downloaded), 1)
                self.assertFalse(any(e.downloaded_successfully for e in downloaded))
                self.assertTrue(all(e.error_message for e in downloaded))

    async def test_process_file_error(self):
        """A process_file crash writes a loadable failed event."""
        for case in ENGINE_CASES:
            with self.subTest(engine=case.engine_cls.__name__):
                status = await self._run(
                    case, process_file_error=RuntimeError("boom")
                )
                self.assertTrue(status.validate_file_status())
                failed = [e for e in status.events if isinstance(e, FailedStatus)]
                self.assertGreaterEqual(len(failed), 1)
                for event in failed:
                    self.assertIn("boom", event.execption)
                    if case.engine_cls is Cerberus:  # FTP listings have no URL
                        self.assertIsNone(event.download_url)
                    else:
                        self.assertTrue(event.download_url)


if __name__ == "__main__":
    unittest.main()
