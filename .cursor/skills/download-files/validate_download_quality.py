#!/usr/bin/env python3
"""
Data quality validation agent.

Runs the scrapers (same pattern as example.py) for each enabled scraper without
limit, collects stats, and writes a report. A separate browser-validation step
can then compare results against the official price-transparency site (see
.cursor/skills/web-surfing and config).
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from il_supermarket_scarper import ScarpingTask, ScraperFactory
from il_supermarket_scarper.utils import _now, Logger

Logger.set_logging_level("WARNING")

# Default report path (relative to repo root)
DEFAULT_REPORT_DIR = Path(__file__).resolve().parent
VALIDATION_REPORT_JSON = "validation_report.json"
VALIDATION_SUMMARY_TXT = "validation_summary.txt"


def _parse_scrapers_arg(scrapers_arg):
    """Parse ENABLED_SCRAPERS env or 'all' or comma-separated names."""
    if not scrapers_arg:
        return ScraperFactory.all_scrapers_name()
    s = scrapers_arg.strip()
    if s.lower() == "all":
        return ScraperFactory.all_scrapers_name()
    return [x.strip() for x in s.split(",") if x.strip()]


async def run_validation(
    enabled_scrapers=None,
    when_date=None,
    report_dir=None,
):
    """
    Run full scrape for each enabled scraper (no limit), collect stats, write report.

    Returns:
        dict: Per-scraper stats (file count, file names, links, sizes) and summary.
    """
    report_dir = report_dir or DEFAULT_REPORT_DIR
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    scraper = ScarpingTask(
        output_configuration={
            "output_mode": "queue",
            "queue_type": "memory",
        },
        status_configuration={"database_type": "json", "base_path": "status_logs"},
        multiprocessing=1,
        enabled_scrapers=enabled_scrapers or ScraperFactory.all_scrapers_name(),
    )

    # No limit, single pass
    scraper.start(limit=None, when_date=when_date or _now(), single_pass=True)

    results = {name: {"files": [], "count": 0, "total_bytes": 0} for name in scraper.runner.enabled_scrapers}

    async def consume_one_queue(name, file_output):
        count = 0
        total_bytes = 0
        async for msg in file_output.queue_handler.get_all_messages():
            count += 1
            file_name = msg.get("file_name", "")
            file_content = msg.get("file_content", b"")
            file_link = msg.get("file_link", "")
            metadata = msg.get("metadata") or {}
            results[name]["files"].append({
                "file_name": file_name,
                "file_link": file_link,
                "size_bytes": len(file_content),
                "metadata": metadata,
            })
            total_bytes += len(file_content)
        results[name]["count"] = count
        results[name]["total_bytes"] = total_bytes

    consume_tasks = [
        consume_one_queue(name, file_output)
        for name, file_output in scraper.consume().items()
    ]
    await asyncio.gather(*consume_tasks)
    scraper.stop()
    scraper.join()

    # Build summary
    summary = {
        "run_at": datetime.utcnow().isoformat() + "Z",
        "scrapers_run": list(results.keys()),
        "per_scraper": {
            name: {
                "file_count": data["count"],
                "total_bytes": data["total_bytes"],
                "file_names": [f["file_name"] for f in data["files"]],
                "links_sample": [f["file_link"] for f in data["files"][:5]],
            }
            for name, data in results.items()
        },
        "full_results_path": str(report_dir / VALIDATION_REPORT_JSON),
    }

    # Write full results (without file content) for browser validation
    full_report = {
        "run_at": summary["run_at"],
        "scrapers_run": summary["scrapers_run"],
        "per_scraper": {
            name: {
                "file_count": data["count"],
                "total_bytes": data["total_bytes"],
                "files": data["files"],
            }
            for name, data in results.items()
        },
    }
    report_json_path = report_dir / VALIDATION_REPORT_JSON
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(full_report, f, ensure_ascii=False, indent=2)

    # Human-readable summary
    summary_lines = [
        f"Validation run at {summary['run_at']}",
        f"Scrapers: {', '.join(summary['scrapers_run'])}",
        "",
    ]
    for name, data in summary["per_scraper"].items():
        summary_lines.append(f"[{name}] files={data['file_count']} bytes={data['total_bytes']}")
        for fn in (data["file_names"] or [])[:10]:
            summary_lines.append(f"  - {fn}")
        if len(data.get("file_names") or []) > 10:
            summary_lines.append(f"  ... and {len(data['file_names']) - 10} more")
        summary_lines.append("")
    summary_path = report_dir / VALIDATION_SUMMARY_TXT
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))

    print(f"Report written to {report_json_path}")
    print(f"Summary written to {summary_path}")
    return full_report


def main():
    enabled = _parse_scrapers_arg(os.environ.get("ENABLED_SCRAPERS", "all"))
    report_dir = os.environ.get("VALIDATION_REPORT_DIR", str(DEFAULT_REPORT_DIR))
    asyncio.run(run_validation(enabled_scrapers=enabled, report_dir=report_dir))


if __name__ == "__main__":
    main()
