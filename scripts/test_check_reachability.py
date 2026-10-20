"""Unit tests for the reachability probe's classification and rendering."""

import asyncio
import json
import os
import tempfile
import unittest
from unittest import mock

from il_supermarket_scarper.utils import Logger

from scripts import check_reachability as reach


def _payload(statuses):
    results = [
        {"scraper": f"CHAIN_{i}", "status": s, "seconds": 1.0, "error": None}
        for i, s in enumerate(statuses)
    ]
    return reach.summarize(results, runner="test runner")


class ClassifyTests(unittest.TestCase):
    """classify() and short_error()."""

    def test_any_download_is_reachable(self):
        """A downloaded file wins over errors seen along the way."""
        self.assertEqual(
            reach.classify(1, ["TimeoutError: [Errno 110]"], False), reach.REACHABLE
        )

    def test_connect_timeout_is_blocked(self):
        """The Cerberus FTP failure seen from outside Israel."""
        errors = [
            "Error reading listing: [Errno 110] Connection timed out\n"
            "Traceback ...\nTimeoutError: [Errno 110] Connection timed out"
        ]
        self.assertEqual(reach.classify(0, errors, False), reach.BLOCKED)
        self.assertIn("Errno 110", reach.short_error(errors))

    def test_refused_and_forbidden_are_blocked(self):
        """Refused connections and HTTP 403 also mean blocked."""
        for error in ["[Errno 111] Connection refused", "HTTP Error 403: Forbidden"]:
            self.assertEqual(reach.classify(0, [error], False), reach.BLOCKED)

    def test_probe_timeout_is_blocked(self):
        """No answer within the time limit counts as blocked."""
        self.assertEqual(reach.classify(0, [], True), reach.BLOCKED)

    def test_other_error_is_error(self):
        """Parsing or code errors are not reported as geo-blocking."""
        self.assertEqual(reach.classify(0, ["KeyError: 'FileNm'"], False), reach.ERROR)

    def test_nothing_is_no_files(self):
        """A clean run that listed nothing."""
        self.assertEqual(reach.classify(0, [], False), reach.NO_FILES)


class ProbeTests(unittest.IsolatedAsyncioTestCase):
    """probe_scraper() with a fake scraper (no network)."""

    async def test_logged_errors_are_attributed_per_chain(self):
        """Concurrent probes only see their own chain's log errors."""

        def fake_scraper(name, fail):
            class _Fake:  # pylint: disable=too-few-public-methods
                def __init__(self, **_):
                    """Accept the scraper constructor arguments."""

                async def scrape(self, limit=None):  # pylint: disable=unused-argument
                    """Fail with a logged connect timeout, or yield one file."""
                    await asyncio.sleep(0.01)
                    if fail:
                        await asyncio.to_thread(
                            Logger.error, f"{name}: [Errno 110] Connection timed out"
                        )
                        return
                    yield mock.Mock(downloaded=True)

            return _Fake

        classes = {
            "GOOD": fake_scraper("GOOD", False),
            "BAD": fake_scraper("BAD", True),
        }
        with mock.patch.object(reach.ScraperFactory, "get", side_effect=classes.get):
            results = await reach.run_probe(["GOOD", "BAD"], timeout=5, concurrency=2)

        by_name = {r["scraper"]: r for r in results}
        self.assertEqual(by_name["GOOD"]["status"], reach.REACHABLE)
        self.assertIsNone(by_name["GOOD"]["error"])
        self.assertEqual(by_name["BAD"]["status"], reach.BLOCKED)
        self.assertIn("BAD", by_name["BAD"]["error"])

    async def test_hanging_scraper_times_out_as_blocked(self):
        """A scraper stuck connecting is cut off at the time limit."""

        class _Hang:  # pylint: disable=too-few-public-methods
            def __init__(self, **_):
                """Accept the scraper constructor arguments."""

            async def scrape(self, limit=None):  # pylint: disable=unused-argument
                """Hang like a connect to a server that never answers."""
                await asyncio.sleep(60)
                yield None

        with mock.patch.object(reach.ScraperFactory, "get", return_value=_Hang):
            result = await reach.probe_scraper("HANG", timeout=0.05)
        self.assertEqual(result["status"], reach.BLOCKED)
        self.assertIn("no file within", result["error"])


class RenderTests(unittest.TestCase):
    """summarize(), render_markdown(), render_badge(), write_outputs()."""

    def test_counts_and_table(self):
        """The table lists every chain and the headline counts match."""
        payload = _payload([reach.REACHABLE, reach.BLOCKED, reach.BLOCKED])
        self.assertEqual(payload["counts"][reach.BLOCKED], 2)
        markdown = reach.render_markdown(payload)
        self.assertIn("**1 of 3**", markdown)
        for i in range(3):
            self.assertIn(f"| CHAIN_{i} |", markdown)

    def test_badge_text_and_color(self):
        """The badge says N/M and turns red when most chains are blocked."""
        badge = reach.render_badge(_payload([reach.REACHABLE] + [reach.BLOCKED] * 3))
        self.assertIn("1/4 reachable", badge)
        self.assertIn("#e05d44", badge)

    def test_write_outputs(self):
        """All three report files are written and the JSON round-trips."""
        payload = _payload([reach.REACHABLE])
        with tempfile.TemporaryDirectory() as tmp:
            reach.write_outputs(payload, tmp)
            self.assertEqual(
                sorted(os.listdir(tmp)),
                ["reachability.json", "reachability.md", "reachability.svg"],
            )
            with open(os.path.join(tmp, "reachability.json"), encoding="utf-8") as f:
                self.assertEqual(json.load(f)["total"], 1)


if __name__ == "__main__":
    unittest.main()
