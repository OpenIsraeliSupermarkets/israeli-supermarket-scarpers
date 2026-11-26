"""Compare status-DB benchmark results of main and a PR (#243).

Reads the JSON files written by `scripts/bench_status_db.py` for each side,
takes the median ms per insert of each side, writes a Markdown table, and
exits 1 when the PR is slower than main by more than both thresholds.

Usage:
    python scripts/compare_status_db_bench.py --base out/main_*.json \
        --branch out/branch_*.json --summary summary.md
"""

import argparse
import json
import statistics
import sys


def side_median(paths):
    """Median ms per insert over all runs of one side."""
    values = []
    for path in paths:
        with open(path, encoding="utf-8") as file:
            values.extend(json.load(file)["runs_ms_per_insert"])
    return statistics.median(values), values


def main(argv=None) -> int:
    """Compare and report; non-zero exit on a regression."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", nargs="+", required=True)
    parser.add_argument("--branch", nargs="+", required=True)
    parser.add_argument("--max-regression", type=float, default=0.15)
    parser.add_argument("--min-delta-ms", type=float, default=5.0)
    parser.add_argument("--summary", default="")
    args = parser.parse_args(argv)

    # Step 1: one number per side
    base, base_runs = side_median(args.base)
    branch, branch_runs = side_median(args.branch)
    delta = branch - base
    ratio = delta / base if base else 0.0

    # Step 2: a regression must cross both the relative and the absolute bar
    regressed = ratio > args.max_regression and delta > args.min_delta_ms
    verdict = "REGRESSION" if regressed else "ok"

    # Step 3: report
    lines = [
        "## Status DB write benchmark (main vs PR)",
        "",
        "| side | median ms / insert | runs |",
        "| --- | --- | --- |",
        f"| main | {base:.1f} | {', '.join(f'{v:.1f}' for v in base_runs)} |",
        f"| PR | {branch:.1f} | {', '.join(f'{v:.1f}' for v in branch_runs)} |",
        "",
        f"Delta: {delta:+.1f} ms ({ratio:+.1%}). Fails above "
        f"+{args.max_regression:.0%} and +{args.min_delta_ms:.0f} ms. **{verdict}**",
    ]
    report = "\n".join(lines)
    print(report)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as file:
            file.write(report + "\n")
    return 1 if regressed else 0


if __name__ == "__main__":
    sys.exit(main())
