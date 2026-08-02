#!/usr/bin/env python3
"""Wall-clock latency benchmark for supermarket scrapers.

Used by CI to compare base (main) vs PR branch performance. Imports the
installed ``il_supermarket_scarper`` package, so the same script can be
mounted into Docker images built from different git refs.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
import time
from typing import Any, Dict, List

from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import DiskFileOutput, Logger
from il_supermarket_scarper.utils.databases import AbstractDataBase
from il_supermarket_scarper.utils.status import _now


def resolve_scrapers(spec: str) -> List[str]:
    """Parse scraper list; ``all`` means every active chain."""
    spec = (spec or "all").strip()
    if spec.lower() == "all":
        return ScraperFactory.all_scrapers_name()
    return [name.strip() for name in spec.split(",") if name.strip()]


class NoOpStatusDatabase(AbstractDataBase):
    """In-memory status DB to avoid disk I/O skewing latency."""

    def __init__(self, database_name):
        super().__init__(database_name)
        self._data: Dict[str, Any] = {}

    def insert_document(self, collection_name, document):
        self._data.setdefault(collection_name, []).append(document)
        self._update_last_modified()

    def insert_documents(self, collection_name, document):
        """Append one document or a list of documents into memory."""
        bucket = self._data.setdefault(collection_name, [])
        if isinstance(document, list):
            bucket.extend(document)
        else:
            bucket.append(document)
        self._update_last_modified()

    def already_downloaded(
        self, collection_name, query
    ):  # pylint: disable=unused-argument
        return False

    def _update_last_modified(self):
        """Stamp in-memory last-modified metadata."""
        self._data.setdefault("_metadata", {})["last_modified"] = _now()

    def get_last_modified(self):
        return self._data.get("_metadata", {}).get("last_modified")


async def bench_scraper(scraper_name: str, limit: int) -> Dict[str, Any]:
    """Run one scraper and return wall-clock metrics."""
    Logger.set_logging_level("ERROR")
    status_db = NoOpStatusDatabase(database_name=scraper_name)
    files_ok = 0
    files_total = 0
    error = None

    with tempfile.TemporaryDirectory(prefix=f"latency_{scraper_name}_") as tmp:
        scraper_cls = ScraperFactory.get(scraper_name)
        if scraper_cls is None:
            return {
                "scraper": scraper_name,
                "error": "scraper disabled",
                "time": 0.0,
                "files": 0,
                "downloaded_ok": 0,
            }

        scraper = scraper_cls(
            file_output=DiskFileOutput(storage_path=tmp),
            status_database=status_db,
        )
        start = time.perf_counter()
        try:
            async for result in scraper.scrape(limit=limit):
                files_total += 1
                if getattr(result, "downloaded", False):
                    files_ok += 1
        except Exception as exc:  # pylint: disable=broad-exception-caught
            error = str(exc)
        elapsed = time.perf_counter() - start

    return {
        "scraper": scraper_name,
        "time": round(elapsed, 3),
        "files": files_total,
        "downloaded_ok": files_ok,
        "files_per_sec": round(files_total / elapsed, 3) if elapsed > 0 else 0.0,
        "error": error,
        "limit": limit,
    }


async def run_benchmark(scrapers: List[str], limit: int) -> Dict[str, Any]:
    """Benchmark all scrapers sequentially (stable network contention)."""
    results = []
    for name in scrapers:
        print(f"Benchmarking {name} (limit={limit})...", flush=True)
        results.append(await bench_scraper(name, limit))
        print(
            f"  -> {results[-1]['time']:.2f}s "
            f"files={results[-1]['files']} ok={results[-1]['downloaded_ok']} "
            f"error={results[-1]['error']}",
            flush=True,
        )

    total = sum(item["time"] for item in results)
    return {
        "ref_label": os.environ.get("LATENCY_REF_LABEL", "unknown"),
        "git_sha": os.environ.get("LATENCY_GIT_SHA", ""),
        "limit": limit,
        "scrapers": results,
        "total_time": round(total, 3),
        "timestamp": _now().isoformat(),
    }


def parse_args():
    """Parse CLI arguments for the latency benchmark."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scrapers",
        default=os.environ.get("LATENCY_SCRAPERS", "all"),
        help="Comma-separated scraper names, or 'all' (default)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=int(os.environ.get("LATENCY_LIMIT", "20")),
        help="Files per scraper (default: 20)",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path to write JSON results",
    )
    return parser.parse_args()


def main():
    """Run the latency benchmark and write JSON results."""
    args = parse_args()
    scrapers = resolve_scrapers(args.scrapers)
    payload = asyncio.run(run_benchmark(scrapers, args.limit))
    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    print(f"Wrote {args.output}", flush=True)


if __name__ == "__main__":
    main()
