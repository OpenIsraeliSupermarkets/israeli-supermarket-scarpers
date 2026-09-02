#!/usr/bin/env python3
"""Fail-fast download check: scrape listed files until the first failure.

Expectation: every file the scraper collects downloads and extracts.
Stops scheduling more files after the first ``extract_succefully=False``.

Uses a fresh dump dir and a status DB that never reports already-downloaded,
so daily-publish ``verified_downloads`` skip cannot hide fetch bugs.

Examples:
  python scripts/validate_downloads.py --scrapers SHUFERSAL
  python scripts/validate_downloads.py --scrapers SHUFERSAL,VICTORY_NEW_SOURCE
  python scripts/validate_downloads.py --per-engine
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from collections import defaultdict
from typing import Any, AsyncGenerator, Dict, List, Optional

from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import Logger, ScrapingResult, _now
from il_supermarket_scarper.utils.databases import AbstractDataBase
from il_supermarket_scarper.utils.file_output import FileOutput


class NoOpStatusDatabase(AbstractDataBase):
    """In-memory status DB that never skips files as already downloaded."""

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
        self._data.setdefault("_metadata", {})["last_modified"] = _now()

    def get_last_modified(self):
        return self._data.get("_metadata", {}).get("last_modified")


class ExtractAndDropFileOutput(FileOutput):
    """Extract to prove the download, then drop bytes so a full scrape fits on disk."""

    def __init__(self, storage_path: str):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    async def save_file(
        self,
        file_link: str,
        file_name: str,
        file_content: bytes,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Decompress in memory; do not persist the artifact."""
        del file_link
        _content, file_name, extract_successfully = await self._extract_if_compressed(
            file_content, file_name
        )
        del _content
        return {
            "file_name": file_name,
            "saved": extract_successfully,
            "extract_successfully": extract_successfully,
            "error": None if extract_successfully else "extract failed",
            "metadata": metadata or {},
        }

    def make_sure_accassible(self):
        """create the storage path"""
        os.makedirs(self.storage_path, exist_ok=True)

    def get_output_location(self) -> str:
        """Return a label for this drop-after-extract output."""
        return f"drop:{self.storage_path}"

    def get_storage_path(self) -> str:
        """Return the storage path for status files and metadata."""
        return self.storage_path

    async def close(self):
        """Close the file output."""


def engine_name(cls) -> str:
    """Best-effort engine label from the class name."""
    return cls.__name__


def listed_factory_members() -> List[str]:
    """All enum members, including stability-disabled ones."""
    return [member.name for member in ScraperFactory]


def resolve_scrapers(args: argparse.Namespace) -> List[str]:
    """Resolve which scrapers to download-check."""
    if args.scrapers:
        return [name.strip() for name in args.scrapers.split(",") if name.strip()]
    if args.all_listed:
        return listed_factory_members()
    if args.per_engine:
        by_engine: Dict[str, List[str]] = defaultdict(list)
        for name in listed_factory_members():
            cls = getattr(ScraperFactory, name).value
            by_engine[engine_name(cls)].append(name)
        return [names[0] for _, names in sorted(by_engine.items())]
    raise SystemExit("Specify --per-engine, --all-listed, or --scrapers")


def make_scraper(enum_name: str):
    """Instantiate scraper class, bypassing ScraperFactory.get stability filter."""
    member = getattr(ScraperFactory, enum_name, None)
    if member is None:
        raise ValueError(f"Unknown scraper {enum_name}")
    return member.value, member


def is_download_ok(result: ScrapingResult) -> bool:
    """True when the file downloaded and extracted."""
    return bool(result.extract_succefully)


def is_source_corrupt_skip(result: ScrapingResult) -> bool:
    """True when the remote file itself is corrupt (not a fetch bug)."""
    return bool(getattr(result, "source_corrupt", False))


async def consume_until_failure(
    results: AsyncGenerator[ScrapingResult, None],
) -> Dict[str, Any]:
    """Drain scrape results; stop at the first extract/download failure.

    Confirmed ``source_corrupt`` results are skipped (counted, not failed):
    the remote published a truncated/bad archive after a complete download.
    """
    summary: Dict[str, Any] = {
        "downloaded": 0,
        "failed": 0,
        "skipped_corrupt": 0,
        "stopped_on_failure": False,
    }
    async for result in results:
        if is_download_ok(result):
            summary["downloaded"] += 1
            if summary["downloaded"] % 25 == 0:
                print(f"    {summary['downloaded']} ok...", flush=True)
            continue
        if is_source_corrupt_skip(result):
            summary["skipped_corrupt"] += 1
            print(
                f"    skip corrupt source file={result.file_name} "
                f"error={result.error}",
                flush=True,
            )
            continue
        summary["failed"] = 1
        summary["stopped_on_failure"] = True
        summary["failed_file"] = result.file_name
        summary["error"] = result.error
        summary["downloaded_flag"] = result.downloaded
        break
    return summary


async def download_one(enum_name: str, limit: Optional[int]) -> Dict[str, Any]:
    """Scrape one factory member until the first failure or completion."""
    cls, member = make_scraper(enum_name)
    row: Dict[str, Any] = {
        "scraper": enum_name,
        "engine": engine_name(cls),
        "class": cls.__name__,
        "enabled_by_factory": ScraperFactory.is_scraper_enabled(member),
        "limit": limit,
        "downloaded": 0,
        "failed": 0,
        "skipped_corrupt": 0,
        "pass": False,
        "stopped_on_failure": False,
    }
    status_db = NoOpStatusDatabase(database_name=f"dl_{enum_name}")
    with tempfile.TemporaryDirectory(prefix=f"dl_{enum_name}_") as tmp:
        scraper = cls(
            file_output=ExtractAndDropFileOutput(storage_path=tmp),
            status_database=status_db,
        )
        row["url"] = getattr(scraper, "url", None) or getattr(scraper, "ftp_host", None)
        try:
            summary = await consume_until_failure(scraper.scrape(limit=limit))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            row["error"] = str(exc)
            return row
    row.update(summary)
    if row.get("failed"):
        row["pass"] = False
    elif row["downloaded"] == 0:
        row["error"] = "no files downloaded"
        row["pass"] = False
    else:
        row["pass"] = True
    return row


async def run(scrapers: List[str], limit: Optional[int]) -> List[Dict[str, Any]]:
    """Download-check each scraper and return per-chain result rows."""
    Logger.set_logging_level(os.environ.get("VALIDATE_LOG_LEVEL", "ERROR"))
    results = []
    for name in scrapers:
        print(f"Downloading {name}...", flush=True)
        row = await download_one(name, limit)
        status = "PASS" if row.get("pass") else "FAIL"
        extra = ""
        if row.get("failed_file"):
            extra = f" file={row['failed_file']} error={row.get('error')}"
        elif row.get("error"):
            extra = f" error={row['error']}"
        skipped = row.get("skipped_corrupt") or 0
        skipped_extra = f" skipped_corrupt={skipped}" if skipped else ""
        print(
            f"  {status} engine={row.get('engine')} "
            f"downloaded={row.get('downloaded')} failed={row.get('failed')}"
            f"{skipped_extra}{extra}",
            flush=True,
        )
        results.append(row)
    return results


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse CLI arguments for fail-fast download validation."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--per-engine",
        action="store_true",
        help="One sample scraper per engine type (includes unstable candidates)",
    )
    group.add_argument(
        "--all-listed",
        action="store_true",
        help="Every ScraperFactory member (ignores stability enablement)",
    )
    group.add_argument(
        "--scrapers",
        help="Comma-separated ScraperFactory names",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max files per scraper (default: all). Prefer all unless smoking.",
    )
    parser.add_argument(
        "--output",
        default="scripts/validation_downloads.json",
        help="JSON report path (default: scripts/validation_downloads.json)",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        default=True,
        help="Exit 1 if any scraper failed a download (default)",
    )
    parser.add_argument(
        "--no-fail-on-error",
        action="store_false",
        dest="fail_on_error",
        help="Always exit 0 after writing the report",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Run download checks, write JSON report, and exit non-zero on failures."""
    args = parse_args(argv)
    scrapers = resolve_scrapers(args)
    results = asyncio.run(run(scrapers, args.limit))
    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, ensure_ascii=False)
    print(f"Wrote {args.output}", flush=True)

    failed = [row for row in results if not row.get("pass")]
    if args.fail_on_error and failed:
        print(f"{len(failed)} scraper(s) failed download check", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
