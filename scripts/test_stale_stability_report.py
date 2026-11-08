"""Unit tests for the weekly stale-stability-rule report."""

import json
import os
import tempfile
import unittest

from scripts import stale_stability_report as report

YELLOW = (
    'STALE_STABILITY_RULE {"files_found": 2, "files_types": ["STORE_FILE"], '
    '"limit": 1, "rule": "Yellow", "scraper": "YELLOW", "store_id": null, '
    '"when_date": null}'
)


def _cofix(day):
    return (
        'STALE_STABILITY_RULE {"files_found": 1, "files_types": null, "limit": 1, '
        '"rule": "PublishOnlyStores", "scraper": "COFIX", "store_id": 3, '
        f'"when_date": "2026-11-0{day}T00:00:00"}}'
    )


def _log(*warnings):
    """A pytest log as CI prints it: logger line plus warnings summary."""
    lines = ["[gw0] [ 10%] PASSED il_supermarket_scarper/x.py::YellowTestCase::t"]
    for warning in warnings:
        lines.append(f"Logger 2026-11-08 WARNING [Main] x.py:f {warning}")
        lines.append(f"  test_cases.py:262: StaleStabilityRuleWarning: {warning}")
    return "\n".join(lines)


class ParseTests(unittest.TestCase):
    """parse_log()"""

    def test_dedupes_within_a_run(self):
        """Logger line and summary line are one finding."""
        payloads = report.parse_log(_log(YELLOW, YELLOW))
        self.assertEqual(len(payloads), 1)
        self.assertEqual(payloads[0]["scraper"], "YELLOW")

    def test_ignores_unrelated_and_broken_lines(self):
        """No marker, or a marker with bad JSON, is skipped."""
        text = "WARNING scraper YELLOW is not stable\nSTALE_STABILITY_RULE {bad json}"
        self.assertEqual(report.parse_log(text), [])


class AggregateTests(unittest.TestCase):
    """aggregate() and render()"""

    def test_counts_runs_not_lines_and_ignores_probe_date(self):
        """COFIX with two probe dates in one run counts as one run."""
        runs = [
            (
                {"databaseId": 1, "createdAt": "2026-11-02T13:00:00Z", "url": "u1"},
                report.parse_log(_log(YELLOW, _cofix(1), _cofix(2))),
            ),
            (
                {"databaseId": 2, "createdAt": "2026-11-03T13:00:00Z", "url": "u2"},
                report.parse_log(_log(YELLOW)),
            ),
        ]
        findings = report.aggregate(runs)
        self.assertEqual([f["scraper"] for f in findings], ["YELLOW", "COFIX"])
        self.assertEqual(len(findings[0]["runs"]), 2)
        self.assertEqual(len(findings[1]["runs"]), 1)
        self.assertEqual(findings[0]["max_files"], 2)

        body = report.render(findings, 2, "2026-11-01")
        self.assertIn("| `YELLOW` | `Yellow` | STORE_FILE |", body)
        self.assertIn("2/2: [2026-11-02](u1), [2026-11-03](u2)", body)


class MainTests(unittest.TestCase):
    """main() end to end on files."""

    def test_writes_body_and_prints_count(self):
        """Runs without a downloaded log are skipped."""
        with tempfile.TemporaryDirectory() as tmp:
            runs = [
                {"databaseId": 7, "createdAt": "2026-11-07T13:00:00Z", "url": "u7"},
                {"databaseId": 8, "createdAt": "2026-11-08T13:00:00Z", "url": "u8"},
            ]
            runs_path = os.path.join(tmp, "runs.json")
            with open(runs_path, "w", encoding="utf-8") as handle:
                json.dump(runs, handle)
            os.makedirs(os.path.join(tmp, "logs", "7"))
            with open(
                os.path.join(tmp, "logs", "7", "pytest-log.txt"), "w", encoding="utf-8"
            ) as handle:
                handle.write(_log(YELLOW))
            out = os.path.join(tmp, "body.md")
            report.main(
                [
                    "--runs",
                    runs_path,
                    "--logs-dir",
                    os.path.join(tmp, "logs"),
                    "--out",
                    out,
                ]
            )
            with open(out, encoding="utf-8") as handle:
                body = handle.read()
        self.assertIn("(1 runs with a pytest log)", body)
        self.assertIn("1/1: [2026-11-07](u7)", body)


if __name__ == "__main__":
    unittest.main()
