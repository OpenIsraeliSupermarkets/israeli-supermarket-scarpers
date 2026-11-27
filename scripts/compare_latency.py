#!/usr/bin/env python3
"""Compare two latency_bench.py JSON outputs (base vs branch).

Exits non-zero when the median scraper (over those with successful downloads
on both sides) is slower on the branch than the allowed threshold. Single
scrapers over --max-regression are listed but don't fail the check (#243).
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from typing import Any, Dict, List, Tuple


def load(path: str) -> Dict[str, Any]:
    """Load a latency_bench JSON payload from disk."""
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def index_by_scraper(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Index scraper result rows by scraper name."""
    return {item["scraper"]: item for item in payload.get("scrapers", [])}


def format_row(cols: List[str], widths: List[int]) -> str:
    """Format one plain-text table row with fixed column widths."""
    return " | ".join(c.ljust(w) for c, w in zip(cols, widths))


def compare(  # pylint: disable=too-many-locals,too-many-statements
    base: Dict[str, Any],
    branch: Dict[str, Any],
    max_regression: float,
    max_median_regression: float,
) -> Tuple[str, List[str]]:
    """Return markdown report and list of regression failure messages.

    Per-chain slowdowns are only flagged: one live site can be slow by chance.
    The check fails when the median chain is slower than
    `max_median_regression`, which is what a slower shared code path (like the
    status DB in #243) looks like: every chain slows down together.
    """
    base_map = index_by_scraper(base)
    branch_map = index_by_scraper(branch)
    scrapers = sorted(set(base_map) | set(branch_map))

    headers = [
        "scraper",
        "base_s",
        "branch_s",
        "delta",
        "delta_%",
        "base_files",
        "branch_files",
        "status",
    ]
    rows: List[List[str]] = []
    failures: List[str] = []
    flagged: List[str] = []
    changes: List[float] = []

    for name in scrapers:
        b = base_map.get(name)
        h = branch_map.get(name)
        if not b or not h:
            rows.append(
                [
                    name,
                    f"{b['time']:.2f}" if b else "n/a",
                    f"{h['time']:.2f}" if h else "n/a",
                    "n/a",
                    "n/a",
                    str(b.get("files", "")) if b else "",
                    str(h.get("files", "")) if h else "",
                    "missing",
                ]
            )
            # A scraper added or removed by the PR has no pair: not a regression
            flagged.append(f"{name} missing on one side")
            continue

        if b.get("error") or h.get("error"):
            rows.append(
                [
                    name,
                    f"{b['time']:.2f}",
                    f"{h['time']:.2f}",
                    "n/a",
                    "n/a",
                    str(b["files"]),
                    str(h["files"]),
                    f"error base={b.get('error')!r} branch={h.get('error')!r}",
                ]
            )
            # Network/site errors: do not fail the comparison job.
            continue

        if b["downloaded_ok"] == 0 or h["downloaded_ok"] == 0:
            rows.append(
                [
                    name,
                    f"{b['time']:.2f}",
                    f"{h['time']:.2f}",
                    "n/a",
                    "n/a",
                    str(b["files"]),
                    str(h["files"]),
                    "no successful downloads",
                ]
            )
            continue

        delta = h["time"] - b["time"]
        pct = (delta / b["time"] * 100.0) if b["time"] > 0 else 0.0
        changes.append(pct)
        if pct > max_regression * 100.0:
            status = f"slower (>{max_regression*100:.0f}%)"
            flagged.append(f"{name} {pct:+.0f}%")
        elif pct < -5:
            status = "improved"
        else:
            status = "ok"

        rows.append(
            [
                name,
                f"{b['time']:.2f}",
                f"{h['time']:.2f}",
                f"{delta:+.2f}",
                f"{pct:+.1f}%",
                str(b["files"]),
                str(h["files"]),
                status,
            ]
        )

    # The verdict: did the typical chain get slower?
    median_pct = statistics.median(changes) if changes else 0.0
    if median_pct > max_median_regression * 100.0:
        failures.append(
            f"median chain is {median_pct:+.1f}% slower "
            f"(allowed +{max_median_regression*100:.0f}%) over {len(changes)} chains"
        )

    widths = [
        max(len(headers[i]), *(len(r[i]) for r in rows)) for i in range(len(headers))
    ]
    lines = [
        "## Latency compare (main vs branch)",
        "",
        f"- Base ref: `{base.get('ref_label', 'base')}` `{base.get('git_sha', '')}`",
        f"- Branch ref: `{branch.get('ref_label', 'branch')}` `{branch.get('git_sha', '')}`",
        f"- Limit: {base.get('limit')} / {branch.get('limit')}",
        f"- Total base: **{base.get('total_time', 0):.2f}s** · "
        f"Total branch: **{branch.get('total_time', 0):.2f}s**",
        f"- Status DB seeded with: {base.get('status_seed', 0)} / "
        f"{branch.get('status_seed', 0)} events",
        f"- Median chain change: **{median_pct:+.1f}%** over {len(changes)} chains "
        f"(fails above +{max_median_regression*100:.0f}%)",
        f"- Chains flagged slower than +{max_regression*100:.0f}% (not failing): "
        f"{', '.join(flagged) or 'none'}",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")

    # Also emit a plain-text table for logs.
    plain = [
        format_row(headers, widths),
        format_row(["-" * w for w in widths], widths),
    ]
    for row in rows:
        plain.append(format_row(row, widths))

    report = "\n".join(lines) + "\n\n```\n" + "\n".join(plain) + "\n```\n"
    return report, failures


def parse_args():
    """Parse CLI arguments for latency comparison."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Base (main) JSON path")
    parser.add_argument("--branch", required=True, help="Branch JSON path")
    parser.add_argument(
        "--max-regression",
        type=float,
        default=float(os.environ.get("LATENCY_MAX_REGRESSION", "0.10")),
        help="Flag regression if branch is slower by this fraction (default 0.10 = 10%%)",
    )
    parser.add_argument(
        "--max-median-regression",
        type=float,
        default=float(os.environ.get("LATENCY_MAX_MEDIAN_REGRESSION", "0.10")),
        help="Fail if the median chain is slower by this fraction (default 0.10)",
    )
    parser.add_argument(
        "--summary",
        default="",
        help="Optional path to write GitHub step summary markdown",
    )
    parser.add_argument(
        "--soft-fail",
        action="store_true",
        default=os.environ.get("LATENCY_SOFT_FAIL", "1") not in ("0", "false", "False"),
        help="Report regressions but exit 0 (default: soft-fail on)",
    )
    parser.add_argument(
        "--no-soft-fail",
        action="store_true",
        help="Exit non-zero when regressions are detected",
    )
    return parser.parse_args()


def main() -> int:
    """Compare base vs branch latency JSON and exit non-zero on regressions."""
    args = parse_args()
    soft_fail = args.soft_fail and not args.no_soft_fail
    base = load(args.base)
    branch = load(args.branch)
    report, failures = compare(
        base, branch, args.max_regression, args.max_median_regression
    )
    if soft_fail:
        report += "\n> Advisory only: regressions do not fail the workflow.\n"
    print(report)
    if args.summary:
        with open(args.summary, "w", encoding="utf-8") as handle:
            handle.write(report)
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            with open(summary_path, "a", encoding="utf-8") as handle:
                handle.write(report)

    if failures:
        print("Latency regressions detected:", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        if soft_fail:
            print(
                "Soft-fail enabled: exiting 0 (non-mandatory check).", file=sys.stderr
            )
            return 0
        return 1
    print("No latency regressions beyond threshold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
