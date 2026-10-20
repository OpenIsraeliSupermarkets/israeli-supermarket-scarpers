#!/usr/bin/env python3
"""Probe which chains can be scraped from the machine this runs on.

Runs a real one-file scrape per active scraper and classifies each chain as
``reachable``, ``blocked``, ``no_files`` or ``error``.
``.github/workflows/reachability.yml`` runs it on a GitHub-hosted runner
(outside Israel) and on the self-hosted CI runner (in Israel), then publishes
the comparison to the ``reports`` branch for the README.

``probe`` writes one location's results. ``report`` compares the
outside-Israel probe with an Israeli one (from the self-hosted CI runner) and
writes ``reachability.json``, ``reachability.md`` (side-by-side table) and
``reachability.svg`` (a badge) to ``--output-dir``. A chain that works in
Israel but not abroad is geo-blocked; one that fails in Israel too is broken.
"""

from __future__ import annotations

import argparse
import asyncio
import contextvars
import json
import logging
import os
import re
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import DiskFileOutput, Logger
from il_supermarket_scarper.utils.scraping.status import _now

from scripts.latency_bench import NoOpStatusDatabase, resolve_scrapers

REACHABLE = "reachable"
BLOCKED = "blocked"
NO_FILES = "no_files"
ERROR = "error"

# Errors that mean the server never answered us or refused us outright, which
# is how the chains' servers treat non-Israeli IPs.
BLOCKED_PATTERNS = re.compile(
    r"Errno 110|Errno 111|Errno 104|timed out|TimeoutError|"
    r"ConnectTimeout|ConnectionRefused|Connection refused|"
    r"ConnectionReset|Connection reset|\b403\b|Forbidden|\b451\b",
    re.IGNORECASE,
)


# Chains are probed concurrently and share one logger, so each probe's errors
# are routed by a context variable (asyncio tasks and to_thread copy it).
_CURRENT_ERRORS: contextvars.ContextVar[Optional[List[str]]] = contextvars.ContextVar(
    "reachability_errors", default=None
)


class _ErrorCollector(logging.Handler):
    """Append error log lines (with tracebacks) to the current probe's list."""

    def __init__(self):
        super().__init__(level=logging.ERROR)

    def emit(self, record):
        sink = _CURRENT_ERRORS.get()
        if sink is None:
            return
        text = record.getMessage()
        if record.exc_info:
            text += "\n" + logging.Formatter().formatException(record.exc_info)
        sink.append(text)


_COLLECTOR = _ErrorCollector()


def classify(downloaded: int, errors: List[str], timed_out: bool) -> str:
    """Return the reachability status for one scraper run."""
    if downloaded > 0:
        return REACHABLE
    if timed_out or any(BLOCKED_PATTERNS.search(e) for e in errors):
        return BLOCKED
    if errors:
        return ERROR
    return NO_FILES


def short_error(errors: List[str]) -> Optional[str]:
    """First line of the most telling error, for the report table."""
    if not errors:
        return None
    blocked = [e for e in errors if BLOCKED_PATTERNS.search(e)]
    chosen = (blocked or errors)[0]
    match = BLOCKED_PATTERNS.search(chosen)
    if match:
        # Show the line that names the network error, not the log prefix.
        for line in chosen.splitlines():
            if BLOCKED_PATTERNS.search(line):
                return line.strip()[:200]
    return chosen.splitlines()[0].strip()[:200]


async def probe_scraper(scraper_name: str, timeout: float) -> Dict[str, Any]:
    """Try to download one file with ``scraper_name`` within ``timeout`` s."""
    errors: List[str] = []
    _CURRENT_ERRORS.set(errors)
    downloaded = 0
    timed_out = False
    start = time.perf_counter()
    scraper_cls = ScraperFactory.get(scraper_name)
    if scraper_cls is None:
        return {
            "scraper": scraper_name,
            "status": ERROR,
            "seconds": 0.0,
            "error": "scraper disabled",
        }
    with tempfile.TemporaryDirectory(prefix=f"reach_{scraper_name}_") as tmp:
        scraper = scraper_cls(
            file_output=DiskFileOutput(storage_path=tmp),
            status_database=NoOpStatusDatabase(database_name=scraper_name),
        )

        async def _run():
            nonlocal downloaded
            async for result in scraper.scrape(limit=1):
                if getattr(result, "downloaded", False):
                    downloaded += 1
                elif getattr(result, "error", None):
                    errors.append(str(result.error))

        try:
            await asyncio.wait_for(_run(), timeout=timeout)
        except asyncio.TimeoutError:
            timed_out = downloaded == 0
        except Exception as exc:  # pylint: disable=broad-exception-caught
            errors.append(f"{type(exc).__name__}: {exc}")

    status = classify(downloaded, errors, timed_out)
    error = short_error(errors)
    if timed_out and error is None:
        error = f"no file within {int(timeout)}s"
    return {
        "scraper": scraper_name,
        "status": status,
        "seconds": round(time.perf_counter() - start, 1),
        "error": error if status != REACHABLE else None,
    }


async def run_probe(
    scrapers: List[str], timeout: float, concurrency: int
) -> List[Dict[str, Any]]:
    """Probe scrapers concurrently (bounded); keep the input order."""
    semaphore = asyncio.Semaphore(concurrency)
    # A blocked connect keeps its worker thread busy until the OS gives up
    # (about two minutes), even after the probe's timeout; size the pool so
    # blocked chains can't starve the rest.
    asyncio.get_running_loop().set_default_executor(
        ThreadPoolExecutor(max_workers=max(32, concurrency * 8))
    )
    if _COLLECTOR not in Logger.logger.handlers:
        Logger.logger.addHandler(_COLLECTOR)

    async def _one(name):
        async with semaphore:
            result = await probe_scraper(name, timeout)
            print(
                f"{name}: {result['status']} ({result['seconds']}s) "
                f"{result['error'] or ''}",
                flush=True,
            )
            return result

    return list(await asyncio.gather(*(_one(name) for name in scrapers)))


def summarize(results: List[Dict[str, Any]], runner: str) -> Dict[str, Any]:
    """Build one location's probe payload (the ``probe`` command's output)."""
    counts = {s: 0 for s in (REACHABLE, BLOCKED, NO_FILES, ERROR)}
    for item in results:
        counts[item["status"]] += 1
    return {
        "generated_at": _now().isoformat(),
        "runner": runner,
        "total": len(results),
        "counts": counts,
        "scrapers": results,
    }


WORKS_EVERYWHERE = "works_everywhere"
GEO_BLOCKED = "geo_blocked"
FAILS_IN_ISRAEL = "fails_in_israel"
NOT_COMPARED = "not_compared"


def verdict(israel: Optional[Dict[str, Any]], outside: Dict[str, Any]) -> str:
    """Compare one chain's probe from Israel with the one from outside."""
    if israel is None:
        return NOT_COMPARED
    if israel["status"] != REACHABLE:
        return FAILS_IN_ISRAEL
    if outside["status"] == REACHABLE:
        return WORKS_EVERYWHERE
    return GEO_BLOCKED


def compare(
    outside: Dict[str, Any], israel: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Merge the outside-Israel probe with the (optional) Israeli one."""
    israel_by_name = (
        {item["scraper"]: item for item in israel["scrapers"]} if israel else {}
    )
    rows = []
    for item in outside["scrapers"]:
        in_israel = israel_by_name.get(item["scraper"]) if israel else None
        rows.append(
            {
                "scraper": item["scraper"],
                "outside": item,
                "israel": in_israel,
                "verdict": verdict(in_israel, item),
            }
        )
    counts = {
        "outside_reachable": outside["counts"][REACHABLE],
        "israel_reachable": israel["counts"][REACHABLE] if israel else None,
    }
    for name in (WORKS_EVERYWHERE, GEO_BLOCKED, FAILS_IN_ISRAEL, NOT_COMPARED):
        counts[name] = sum(1 for row in rows if row["verdict"] == name)
    return {
        "generated_at": _now().isoformat(),
        "runners": {
            "outside": outside["runner"],
            "israel": israel["runner"] if israel else None,
        },
        "total": len(rows),
        "counts": counts,
        "scrapers": rows,
    }


_ICONS = {REACHABLE: "✅", BLOCKED: "⛔", NO_FILES: "⚪", ERROR: "⚠️"}
_VERDICT_TEXT = {
    WORKS_EVERYWHERE: "works everywhere",
    GEO_BLOCKED: "**geo-blocked**",
    FAILS_IN_ISRAEL: "**fails in Israel too** (not geo-blocking)",
    NOT_COMPARED: "",
}
_VERDICT_ORDER = [GEO_BLOCKED, FAILS_IN_ISRAEL, NOT_COMPARED, WORKS_EVERYWHERE]


def _cell(probe: Optional[Dict[str, Any]]) -> str:
    if probe is None:
        return "not run"
    text = f"{_ICONS[probe['status']]} {probe['status']}"
    if probe.get("error"):
        text += f" ({probe['error']})"
    return text.replace("|", "\\|")


def render_markdown(report: Dict[str, Any]) -> str:
    """Render the side-by-side per-chain table."""
    counts = report["counts"]
    total = report["total"]
    runners = report["runners"]
    lines = [
        "# Scraper reachability: Israel vs outside Israel",
        "",
        f"Generated {report['generated_at']}.",
        f"Outside Israel: {runners['outside']}.",
        f"Israel: {runners['israel'] or 'not run this time'}.",
        "",
        f"**{counts['outside_reachable']} of {total}** chains could download a "
        "file from outside Israel.",
    ]
    if runners["israel"]:
        lines += [
            f"From Israel: {counts['israel_reachable']} of {total}. "
            f"Geo-blocked (work in Israel only): {counts[GEO_BLOCKED]}. "
            f"Failing in Israel too: {counts[FAILS_IN_ISRAEL]}.",
        ]
    lines += [
        "",
        "| Chain | Israel | Outside Israel | Verdict |",
        "|---|---|---|---|",
    ]
    rows = sorted(
        report["scrapers"],
        key=lambda r: (_VERDICT_ORDER.index(r["verdict"]), r["scraper"]),
    )
    for row in rows:
        lines.append(
            f"| {row['scraper']} | {_cell(row['israel'])} "
            f"| {_cell(row['outside'])} | {_VERDICT_TEXT[row['verdict']]} |"
        )
    return "\n".join(lines) + "\n"


def render_badge(report: Dict[str, Any]) -> str:
    """Render a flat shields-style SVG badge: 'outside Israel | N/M reachable'."""
    reachable = report["counts"]["outside_reachable"]
    total = report["total"]
    label = "outside Israel"
    value = f"{reachable}/{total} reachable"
    ratio = reachable / total if total else 0
    color = "#4c1" if ratio >= 0.9 else "#dfb317" if ratio >= 0.5 else "#e05d44"
    left = 6 * len(label) + 10
    right = 6 * len(value) + 10
    width = left + right
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" '
        f'role="img" aria-label="{label}: {value}">'
        f'<rect width="{left}" height="20" fill="#555"/>'
        f'<rect x="{left}" width="{right}" height="20" fill="{color}"/>'
        '<g fill="#fff" text-anchor="middle" '
        'font-family="Verdana,DejaVu Sans,sans-serif" font-size="11">'
        f'<text x="{left / 2}" y="14">{label}</text>'
        f'<text x="{left + right / 2}" y="14">{value}</text>'
        "</g></svg>\n"
    )


def write_outputs(report: Dict[str, Any], output_dir: str) -> None:
    """Write the JSON, Markdown table and SVG badge."""
    os.makedirs(output_dir, exist_ok=True)
    with open(
        os.path.join(output_dir, "reachability.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    with open(os.path.join(output_dir, "reachability.md"), "w", encoding="utf-8") as f:
        f.write(render_markdown(report))
    with open(os.path.join(output_dir, "reachability.svg"), "w", encoding="utf-8") as f:
        f.write(render_badge(report))


def _load(path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_args(argv=None):
    """Parse CLI arguments for the ``probe`` and ``report`` commands."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    probe = commands.add_parser("probe", help="Probe the chains from this machine")
    probe.add_argument(
        "--scrapers",
        default="all",
        help="Comma-separated scraper names, or 'all' (default)",
    )
    probe.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Seconds allowed per chain (default: 300)",
    )
    probe.add_argument(
        "--concurrency", type=int, default=6, help="Chains probed at once (default: 6)"
    )
    probe.add_argument(
        "--runner",
        default=os.environ.get("REACHABILITY_RUNNER", "an unknown host"),
        help="Where this ran, shown in the report",
    )
    probe.add_argument("--output", required=True, help="Probe JSON to write")

    report = commands.add_parser("report", help="Build the report from probe files")
    report.add_argument("--outside", required=True, help="Probe JSON from abroad")
    report.add_argument(
        "--israel", help="Probe JSON from an Israeli host (optional; may be missing)"
    )
    report.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def main(argv=None):
    """Run ``probe`` (one location) or ``report`` (compare and render)."""
    args = parse_args(argv)
    if args.command == "probe":
        Logger.set_logging_level("ERROR")
        results = asyncio.run(
            run_probe(resolve_scrapers(args.scrapers), args.timeout, args.concurrency)
        )
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(summarize(results, args.runner), f, indent=2, ensure_ascii=False)
        print(f"Wrote probe results to {args.output}", flush=True)
        return
    outside = _load(args.outside)
    if outside is None:
        raise SystemExit(f"Missing outside-Israel probe file: {args.outside}")
    write_outputs(compare(outside, _load(args.israel)), args.output_dir)
    print(f"Wrote reachability report to {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
