import argparse
import time
import json
import datetime
import pstats
import cProfile
import io
import asyncio
import os
from collections import defaultdict

from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import DiskFileOutput, Logger
from il_supermarket_scarper.utils.status import _now
from il_supermarket_scarper.utils.databases import AbstractDataBase


# Representative scrapers across engine types for optimization comparison.
DEFAULT_SCRAPERS = [
    ScraperFactory.SUPER_PHARM.name,  # MultiPageWeb (2-step download)
    ScraperFactory.SHUFERSAL.name,  # MultiPageWeb
    ScraperFactory.RAMI_LEVY.name,  # Cerberus
    ScraperFactory.BAREKET.name,  # Bina
    ScraperFactory.VICTORY_NEW_SOURCE.name,  # ApiWebEngine
    ScraperFactory.YELLOW.name,  # Cerberus-like / publish price family
]


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that properly formats datetime objects."""

    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.isoformat()
        if isinstance(o, datetime.date):
            return o.isoformat()
        if isinstance(o, datetime.time):
            return o.isoformat()
        try:
            return super().default(o)
        except TypeError:
            return str(o)


class NoOpStatusDatabase(AbstractDataBase):
    """In-memory database for stress testing performance.
    Collects all status data in memory without file I/O, then dumps to results."""

    def __init__(self, database_name):
        super().__init__(database_name)
        self._data = {}

    def insert_document(self, collection_name, document):
        """Store document in memory collection."""
        if collection_name not in self._data:
            self._data[collection_name] = []
        self._data[collection_name].append(document)
        self._update_last_modified()

    def insert_documents(self, collection_name, document):
        """Store multiple documents in memory collection."""
        if collection_name not in self._data:
            self._data[collection_name] = []
        if isinstance(document, list):
            self._data[collection_name].extend(document)
        else:
            self._data[collection_name].append(document)
        self._update_last_modified()

    def already_downloaded(
        self, collection_name, query
    ):  # pylint: disable=unused-argument
        """Always return False - assume nothing is downloaded."""
        return False

    def _update_last_modified(self):
        """Update the last modified timestamp to current time."""
        if "_metadata" not in self._data:
            self._data["_metadata"] = {}
        self._data["_metadata"]["last_modified"] = _now()

    def get_last_modified(self):
        """Get the last modified timestamp when scraper last wrote to this database."""
        if "_metadata" in self._data and "last_modified" in self._data["_metadata"]:
            return self._data["_metadata"]["last_modified"]
        return None

    def get_all_data(self):
        """Get all collected status data as a dictionary matching JsonDataBase format."""
        return dict(sorted(self._data.items()))


def _parse_stat_line(line):
    """Parse a pstats print_stats line into structured fields."""
    parts = line.split()
    if len(parts) < 6:
        return None
    return {
        "function": parts[-1],
        "ncalls": parts[0],
        "tottime": float(parts[1]),
        "tottime_per_call": float(parts[2]),
        "cumtime": float(parts[3]),
        "cumtime_per_call": float(parts[4]),
    }


def format_stats_as_json(profile, project_name, top_n=40):
    """get the stats from the profiler and format them as json"""
    stream = io.StringIO()
    ps = pstats.Stats(profile, stream=stream)
    ps.sort_stats(pstats.SortKey.CUMULATIVE)
    ps.print_stats()

    project_stats = []
    for line in stream.getvalue().splitlines():
        if project_name not in line:
            continue
        parsed = _parse_stat_line(line)
        if parsed:
            project_stats.append(parsed)

    return project_stats[:top_n]


def categorize_hotspots(project_stats):
    """Group project stats into optimization buckets."""
    buckets = defaultdict(lambda: {"tottime": 0.0, "cumtime": 0.0, "functions": []})
    rules = (
        ("network", ("connection.py", "session_with", "url_retrieve", "wget_file")),
        ("listing", ("multipage_web.py", "collect_files", "generate_all_files")),
        ("download", ("retrieve_file", "save_and_extract", "process_file")),
        ("gzip_io", ("gzip_utils.py", "file_output.py", "_extract_if", "_write_file")),
        ("retry_sleep", ("retry.py", "asyncio.sleep", "time.sleep")),
        ("status_db", ("scraper_status.py", "databases/", "NoOpStatusDatabase")),
    )

    for stat in project_stats:
        matched = "other"
        func = stat["function"]
        for name, needles in rules:
            if any(n in func for n in needles):
                matched = name
                break
        buckets[matched]["tottime"] += stat["tottime"]
        buckets[matched]["cumtime"] += stat["cumtime"]
        if len(buckets[matched]["functions"]) < 5:
            buckets[matched]["functions"].append(
                {
                    "function": func,
                    "tottime": stat["tottime"],
                    "cumtime": stat["cumtime"],
                    "ncalls": stat["ncalls"],
                }
            )

    return dict(
        sorted(buckets.items(), key=lambda item: item[1]["cumtime"], reverse=True)
    )


def summarize_status(status_data):
    """Extract high-level counts from status collections."""
    summary = {}
    for key, value in status_data.items():
        if key == "_metadata":
            continue
        if isinstance(value, list):
            summary[key] = len(value)
    downloaded = status_data.get("downloaded", []) or status_data.get(
        "downloaded_files", []
    )
    failed = status_data.get("failed", []) or status_data.get("failed_files", [])
    if isinstance(downloaded, list):
        summary["downloaded_count"] = len(downloaded)
    if isinstance(failed, list):
        summary["failed_count"] = len(failed)
    return summary


async def run_scraper(scraper_name, limit):
    """Run one scraper under cProfile and return metrics."""
    Logger.set_logging_level("WARNING")

    async def full_execution():
        files = []
        error = None
        status_database = None
        try:
            status_database = NoOpStatusDatabase(database_name=scraper_name)
            storage_path = f"temp/{scraper_name}"
            initer = ScraperFactory.get(scraper_name)(
                file_output=DiskFileOutput(storage_path=storage_path),
                status_database=status_database,
            )
            async for result in initer.scrape(limit=limit):
                files.append(result)
        except Exception as e:  # pylint: disable=broad-exception-caught
            error = str(e)

        status_data = status_database.get_all_data() if status_database else {}
        return files, error, status_data

    execution_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start_time = time.time()
    pr = cProfile.Profile()
    pr.enable()
    files, error, status_data = await full_execution()
    pr.disable()
    end_time = time.time()

    elapsed = end_time - start_time
    project_stats = format_stats_as_json(pr, "israeli-supermarket-scarpers")
    downloaded_ok = sum(1 for f in files if getattr(f, "downloaded", False))
    extracted_ok = sum(1 for f in files if getattr(f, "extract_succefully", False))

    return {
        "status": project_stats,
        "hotspots": categorize_hotspots(project_stats),
        "execution_time": execution_time,
        "start_time": start_time,
        "end_time": end_time,
        "time": elapsed,
        "files": len(files),
        "downloaded_ok": downloaded_ok,
        "extracted_ok": extracted_ok,
        "files_per_sec": (len(files) / elapsed) if elapsed > 0 else 0,
        "error": error,
        "status_summary": summarize_status(status_data),
        "status_data": status_data,
    }


def print_report(results, limit):
    """Print a concise optimization-oriented report."""
    print("\n" + "=" * 72)
    print(f"STRESS TEST REPORT (limit={limit})")
    print("=" * 72)

    ranked = sorted(results.items(), key=lambda item: item[1]["time"], reverse=True)
    print(f"{'scraper':32} {'sec':>8} {'files':>6} {'ok':>6} {'f/s':>7} {'error'}")
    print("-" * 72)
    for name, data in ranked:
        err = (data.get("error") or "")[:28]
        print(
            f"{name:32} {data['time']:8.1f} {data['files']:6d} "
            f"{data['downloaded_ok']:6d} {data['files_per_sec']:7.2f} {err}"
        )

    print("\nTop hotspot buckets per scraper (by cumtime):")
    for name, data in ranked:
        print(f"\n[{name}] wall={data['time']:.1f}s files={data['files']}")
        hotspots = data.get("hotspots") or {}
        for bucket, info in list(hotspots.items())[:4]:
            print(
                f"  - {bucket:12} cum={info['cumtime']:.2f}s "
                f"tot={info['tottime']:.2f}s"
            )
            for func in info["functions"][:2]:
                print(
                    f"      {func['function']} "
                    f"(cum={func['cumtime']:.2f}s, n={func['ncalls']})"
                )
        top = (data.get("status") or [])[:5]
        if top:
            print("  top functions:")
            for func in top:
                print(
                    f"      {func['function']} "
                    f"cum={func['cumtime']} tot={func['tottime']} n={func['ncalls']}"
                )


def parse_args():
    """CLI / env configuration for the stress test."""
    parser = argparse.ArgumentParser(description="Profile supermarket scrapers")
    parser.add_argument(
        "--limit",
        type=int,
        default=int(os.getenv("STRESS_LIMIT", "30")),
        help="Max files to download per scraper (default: 30)",
    )
    parser.add_argument(
        "--scrapers",
        type=str,
        default=os.getenv("STRESS_SCRAPERS", ",".join(DEFAULT_SCRAPERS)),
        help="Comma-separated scraper names, or 'all'",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="stress_test_results.json",
        help="Path for JSON results",
    )
    return parser.parse_args()


async def main():
    """Main function to run stress tests on scrapers."""
    args = parse_args()

    if args.scrapers.strip().lower() == "all":
        scrapers = ScraperFactory.all_scrapers_name()
    else:
        scrapers = [s.strip() for s in args.scrapers.split(",") if s.strip()]

    results = {}
    for scraper_name in scrapers:
        print(f"\n>>> Profiling {scraper_name} (limit={args.limit})...")
        results[scraper_name] = await run_scraper(scraper_name, args.limit)
        data = results[scraper_name]
        print(
            f"<<< {scraper_name}: {data['time']:.1f}s, "
            f"{data['files']} files, error={data['error']}"
        )

        # Persist incrementally so a mid-run failure still leaves data.
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, cls=DateTimeEncoder, indent=2)

    print_report(results, args.limit)
    print(f"\nFull results written to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
