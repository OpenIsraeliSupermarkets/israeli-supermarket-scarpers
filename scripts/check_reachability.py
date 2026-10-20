#!/usr/bin/env python3
"""Probe which chains can be scraped from the machine this runs on.

Runs a real one-file scrape per active scraper and classifies each chain as
``reachable``, ``blocked``, ``no_files`` or ``error``. Run on a GitHub-hosted
runner (outside Israel) by ``.github/workflows/reachability.yml``, which
publishes the outputs to the ``reports`` branch for the README.

Outputs in ``--output-dir``: ``reachability.json``, ``reachability.md`` and
``reachability.svg`` (a badge).
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
    """Build the JSON payload published to the reports branch."""
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


_ICONS = {REACHABLE: "✅", BLOCKED: "⛔", NO_FILES: "⚪", ERROR: "⚠️"}


def render_markdown(payload: Dict[str, Any]) -> str:
    """Render the per-chain table."""
    counts = payload["counts"]
    lines = [
        "# Scraper reachability from outside Israel",
        "",
        f"Generated {payload['generated_at']} on {payload['runner']}.",
        "",
        f"**{counts[REACHABLE]} of {payload['total']}** chains could download a "
        f"file from here. Blocked: {counts[BLOCKED]} (connection timed out, "
        f"refused or forbidden). No files listed: {counts[NO_FILES]}. "
        f"Other errors: {counts[ERROR]}.",
        "",
        "From an Israeli IP all active chains are expected to work; see the "
        "daily test suite.",
        "",
        "| Chain | Status | Seconds | Error |",
        "|---|---|---|---|",
    ]
    for item in sorted(payload["scrapers"], key=lambda i: (i["status"], i["scraper"])):
        error = (item.get("error") or "").replace("|", "\\|")
        lines.append(
            f"| {item['scraper']} | {_ICONS[item['status']]} {item['status']} "
            f"| {item['seconds']} | {error} |"
        )
    return "\n".join(lines) + "\n"


def render_badge(payload: Dict[str, Any]) -> str:
    """Render a flat shields-style SVG badge: 'outside Israel | N/M reachable'."""
    reachable = payload["counts"][REACHABLE]
    total = payload["total"]
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


def write_outputs(payload: Dict[str, Any], output_dir: str) -> None:
    """Write the JSON, Markdown table and SVG badge."""
    os.makedirs(output_dir, exist_ok=True)
    with open(
        os.path.join(output_dir, "reachability.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    with open(os.path.join(output_dir, "reachability.md"), "w", encoding="utf-8") as f:
        f.write(render_markdown(payload))
    with open(os.path.join(output_dir, "reachability.svg"), "w", encoding="utf-8") as f:
        f.write(render_badge(payload))


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scrapers",
        default="all",
        help="Comma-separated scraper names, or 'all' (default)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Seconds allowed per chain (default: 300)",
    )
    parser.add_argument(
        "--concurrency", type=int, default=6, help="Chains probed at once (default: 6)"
    )
    parser.add_argument(
        "--runner",
        default=os.environ.get("REACHABILITY_RUNNER", "an unknown host"),
        help="Where this ran, shown in the report",
    )
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main():
    """Probe every scraper and write the report files."""
    args = parse_args()
    Logger.set_logging_level("ERROR")
    results = asyncio.run(
        run_probe(resolve_scrapers(args.scrapers), args.timeout, args.concurrency)
    )
    payload = summarize(results, args.runner)
    write_outputs(payload, args.output_dir)
    print(f"Wrote reachability report to {args.output_dir}", flush=True)


if __name__ == "__main__":
    main()
