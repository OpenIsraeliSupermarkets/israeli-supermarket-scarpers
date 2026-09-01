"""Unit tests for fail-fast download validation helpers."""

import unittest

from il_supermarket_scarper.utils import ScrapingResult

from scripts.validate_downloads import (
    consume_until_failure,
    is_download_ok,
    is_source_corrupt_skip,
)


def _ok(name: str) -> ScrapingResult:
    return ScrapingResult(
        file_name=name,
        downloaded=True,
        extract_succefully=True,
    )


def _fail(name: str, error: str) -> ScrapingResult:
    return ScrapingResult(
        file_name=name,
        downloaded=False,
        extract_succefully=False,
        error=error,
    )


def _corrupt(name: str) -> ScrapingResult:
    return ScrapingResult(
        file_name=name,
        downloaded=True,
        extract_succefully=False,
        error="source corrupt after 3 downloads: extract failed",
        source_corrupt=True,
    )


class TestDownloadHelpers(unittest.IsolatedAsyncioTestCase):
    """Fail-fast contract for validate_downloads."""

    def test_is_download_ok_requires_extract(self):
        """Downloaded but not extracted is a failure."""
        self.assertTrue(is_download_ok(_ok("a")))
        self.assertFalse(
            is_download_ok(
                ScrapingResult(
                    file_name="a",
                    downloaded=True,
                    extract_succefully=False,
                    error="extract failed",
                )
            )
        )
        self.assertFalse(is_download_ok(_corrupt("a")))
        self.assertTrue(is_source_corrupt_skip(_corrupt("a")))
        self.assertFalse(is_source_corrupt_skip(_fail("a", "wget")))

    async def test_consume_stops_on_first_failure(self):
        """Later files must not be pulled after the first failed result."""
        pulled = []

        async def results():
            items = (
                _ok("one"),
                _ok("two"),
                _fail("three", "wget: not found"),
                _ok("four"),
            )
            for item in items:
                pulled.append(item.file_name)
                yield item

        summary = await consume_until_failure(results())
        self.assertEqual(summary["downloaded"], 2)
        self.assertEqual(summary["failed"], 1)
        self.assertTrue(summary["stopped_on_failure"])
        self.assertEqual(summary["failed_file"], "three")
        self.assertEqual(summary["error"], "wget: not found")
        self.assertEqual(pulled, ["one", "two", "three"])

    async def test_consume_skips_source_corrupt(self):
        """Confirmed remote-corrupt archives do not fail-fast the chain."""
        pulled = []

        async def results():
            items = (_ok("one"), _corrupt("bad.gz"), _ok("three"))
            for item in items:
                pulled.append(item.file_name)
                yield item

        summary = await consume_until_failure(results())
        self.assertEqual(summary["downloaded"], 2)
        self.assertEqual(summary["skipped_corrupt"], 1)
        self.assertEqual(summary["failed"], 0)
        self.assertFalse(summary["stopped_on_failure"])
        self.assertEqual(pulled, ["one", "bad.gz", "three"])

    async def test_consume_all_ok(self):
        """A full successful drain reports no failure."""

        async def results():
            yield _ok("one")
            yield _ok("two")

        summary = await consume_until_failure(results())
        self.assertEqual(summary["downloaded"], 2)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["skipped_corrupt"], 0)
        self.assertFalse(summary["stopped_on_failure"])


if __name__ == "__main__":
    unittest.main()
