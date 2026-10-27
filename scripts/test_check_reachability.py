"""Unit tests for the reachability probe's classification and rendering."""

import asyncio
import json
import os
import tempfile
import unittest
from datetime import datetime
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

    async def test_clean_empty_listing_is_no_files(self):
        """A clean empty scrape is a missing-file failure."""

        class _Empty:  # pylint: disable=too-few-public-methods
            utilize_date_param = False

            def __init__(self, **_):
                """Accept the scraper constructor arguments."""

            async def scrape(self, limit=None):  # pylint: disable=unused-argument
                """List nothing and raise nothing."""
                for _item in ():
                    yield _item

        with mock.patch.object(reach.ScraperFactory, "get", return_value=_Empty):
            result = await reach.probe_scraper("EMPTY", timeout=5)
        self.assertEqual(result["status"], reach.NO_FILES)

    async def test_known_empty_listing_is_not_a_failure(self):
        """A stability rule turns a clean empty scrape into expected_empty."""

        class _Empty:  # pylint: disable=too-few-public-methods
            utilize_date_param = True

            def __init__(self, **_):
                """Accept the scraper constructor arguments."""

            async def scrape(self, limit=None):  # pylint: disable=unused-argument
                """List nothing and raise nothing."""
                for _item in ():
                    yield _item

        when_date = datetime(2026, 9, 17, 0, 30)
        with mock.patch.object(
            reach.ScraperFactory, "get", return_value=_Empty
        ), mock.patch.object(
            reach, "_now", return_value=when_date
        ), mock.patch.object(
            reach.ScraperStability,
            "is_validate_scraper_found_no_files",
            return_value=True,
        ) as expected:
            result = await reach.probe_scraper("VICTORY_NEW_SOURCE", timeout=5)
        self.assertEqual(result["status"], reach.EXPECTED_EMPTY)
        expected.assert_called_once_with(
            "VICTORY_NEW_SOURCE",
            limit=1,
            when_date=when_date,
            utilize_date_param=True,
        )


class CompareTests(unittest.TestCase):
    """compare() and verdict(): Israel vs outside Israel."""

    def test_verdicts(self):
        """Geo-blocked only when the chain works from Israel."""
        outside = _payload([reach.REACHABLE, reach.BLOCKED, reach.BLOCKED])
        israel = _payload([reach.REACHABLE, reach.REACHABLE, reach.ERROR])
        report = reach.compare(outside, israel)
        verdicts = [row["verdict"] for row in report["scrapers"]]
        self.assertEqual(
            verdicts,
            [reach.WORKS_EVERYWHERE, reach.GEO_BLOCKED, reach.FAILS_IN_ISRAEL],
        )
        self.assertEqual(report["counts"]["israel_reachable"], 2)
        self.assertEqual(report["counts"][reach.GEO_BLOCKED], 1)

    def test_israel_probe_missing(self):
        """The report still builds when the Israeli runner didn't run."""
        report = reach.compare(_payload([reach.REACHABLE, reach.BLOCKED]))
        self.assertIsNone(report["runners"]["israel"])
        self.assertEqual(report["counts"][reach.NOT_COMPARED], 2)
        self.assertIn("not run", reach.render_markdown(report))

    def test_chain_missing_from_israel_probe(self):
        """A chain absent from the Israeli probe is not called geo-blocked."""
        outside = _payload([reach.BLOCKED, reach.BLOCKED])
        israel = _payload([reach.REACHABLE])
        report = reach.compare(outside, israel)
        self.assertEqual(report["scrapers"][1]["verdict"], reach.NOT_COMPARED)

    def test_expected_empty_in_israel_is_not_a_failure(self):
        """A known-empty Israel probe is not 'fails in Israel'."""
        outside = _payload([reach.BLOCKED, reach.NO_FILES, reach.EXPECTED_EMPTY])
        israel = _payload([reach.EXPECTED_EMPTY, reach.NO_FILES, reach.REACHABLE])
        report = reach.compare(outside, israel)
        verdicts = [row["verdict"] for row in report["scrapers"]]
        self.assertEqual(
            verdicts,
            [reach.EXPECTED_EMPTY, reach.FAILS_IN_ISRAEL, reach.WORKS_EVERYWHERE],
        )
        self.assertEqual(report["counts"][reach.FAILS_IN_ISRAEL], 1)
        self.assertEqual(report["counts"][reach.EXPECTED_EMPTY], 1)
        self.assertIn("not a failure", reach.render_markdown(report))


class RenderTests(unittest.TestCase):
    """render_markdown(), render_badge(), write_outputs(), the CLI."""

    def test_counts_and_table(self):
        """The table lists every chain side by side; geo-blocked rows first."""
        report = reach.compare(
            _payload([reach.REACHABLE, reach.BLOCKED, reach.BLOCKED]),
            _payload([reach.REACHABLE, reach.REACHABLE, reach.REACHABLE]),
        )
        markdown = reach.render_markdown(report)
        self.assertIn("**1 of 3**", markdown)
        self.assertIn("Geo-blocked (work in Israel only): 2", markdown)
        self.assertIn("| Chain | Israel | Outside Israel | Verdict |", markdown)
        for i in range(3):
            self.assertIn(f"| CHAIN_{i} |", markdown)
        self.assertLess(markdown.index("CHAIN_1"), markdown.index("CHAIN_0"))

    def test_badge_text_and_color(self):
        """The badge says N/M and turns red when most chains are blocked."""
        report = reach.compare(_payload([reach.REACHABLE] + [reach.BLOCKED] * 3))
        badge = reach.render_badge(report)
        self.assertIn("1/4 reachable", badge)
        self.assertIn("#e05d44", badge)

    def test_report_command_writes_outputs(self):
        """`report` reads both probe files and writes the three outputs."""
        with tempfile.TemporaryDirectory() as tmp:
            for name, statuses in (
                ("outside", [reach.BLOCKED]),
                ("israel", [reach.REACHABLE]),
            ):
                with open(
                    os.path.join(tmp, f"{name}.json"), "w", encoding="utf-8"
                ) as f:
                    json.dump(_payload(statuses), f)
            out = os.path.join(tmp, "out")
            reach.main(
                [
                    "report",
                    "--outside",
                    os.path.join(tmp, "outside.json"),
                    "--israel",
                    os.path.join(tmp, "israel.json"),
                    "--output-dir",
                    out,
                ]
            )
            self.assertEqual(
                sorted(os.listdir(out)),
                ["reachability.json", "reachability.md", "reachability.svg"],
            )
            with open(os.path.join(out, "reachability.json"), encoding="utf-8") as f:
                self.assertEqual(
                    json.load(f)["scrapers"][0]["verdict"], reach.GEO_BLOCKED
                )


if __name__ == "__main__":
    unittest.main()
