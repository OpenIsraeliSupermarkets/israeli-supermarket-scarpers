"""Benchmark the JSON status DB write path (#241).

The scraper writes a status document for every file it downloads, and the
parsers reuse the same JsonDataBase for their own status. This times
`insert_document` on a database that already holds a realistic number of
documents, so a slower write path (an fsync, an extra rewrite) shows up.

Usage:
    python scripts/bench_status_db.py --existing 5000 --inserts 200 --output out.json

Runs offline, on a temp directory. Prints ms per insert (median of --repeat).
"""

import argparse
import json
import os
import statistics
import sys
import tempfile
import time

from il_supermarket_scarper.utils.databases.json_file import JsonDataBase


def make_document(index: int) -> dict:
    """A status document shaped like the scraper's download events."""
    return {
        "file_name": f"PriceFull7290027600007-001-{index:03d}-20261126-020000.gz",
        "link": f"https://example.invalid/pricefull/{index}.gz",
        "status": "downloaded",
        "size": 460822 + index,
        "extract_succefully": True,
        "error": None,
        "restart_and_retry": False,
        "when": "2026-11-26T04:25:45.557000+02:00",
    }


def run_once(existing: int, inserts: int) -> float:
    """Seed a DB with `existing` documents, then time `inserts` single inserts.
    Returns milliseconds per insert."""
    with tempfile.TemporaryDirectory() as folder:
        database = JsonDataBase("bench_chain", base_path=folder)

        # Step 1: seed the database in one write, like a day of prior downloads
        database.insert_documents("events", [make_document(i) for i in range(existing)])

        # Step 2: time one insert per downloaded file
        start = time.perf_counter()
        for i in range(inserts):
            database.insert_document("events", make_document(existing + i))
        elapsed = time.perf_counter() - start
    return elapsed * 1000 / inserts


def main(argv=None) -> int:
    """Run the benchmark and write the result as JSON."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--existing", type=int, default=5000)
    parser.add_argument("--inserts", type=int, default=200)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--output", default="")
    parser.add_argument("--label", default=os.environ.get("BENCH_LABEL", ""))
    args = parser.parse_args(argv)

    runs = [run_once(args.existing, args.inserts) for _ in range(args.repeat)]
    result = {
        "label": args.label,
        "existing": args.existing,
        "inserts": args.inserts,
        "runs_ms_per_insert": [round(r, 3) for r in runs],
        "median_ms_per_insert": round(statistics.median(runs), 3),
    }
    print(json.dumps(result))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as file:
            json.dump(result, file, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
