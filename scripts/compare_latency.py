#!/usr/bin/env python3
"""Compare two latency_bench.py JSON outputs (base vs branch).

Exits non-zero if the branch is slower than base beyond the allowed threshold
on any scraper that produced successful downloads on both sides.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Tuple


def load(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def index_by_scraper(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {item["scraper"]: item for item in payload.get("scrapers", [])}


def format_row(cols: List[str], widths: List[int]) -> str:
    return " | ".join(c.ljust(w) for c, w in zip(cols, widths))


def compare(
    base: Dict[str, Any],
    branch: Dict[str, Any],
    max_regression: float,
) -> Tuple[str, List[str]]:
    """Return markdown report and list of regression failure messages."""
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
            failures.append(f"{name}: missing result on one side")
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
        if pct > max_regression * 100.0:
            status = f"REGRESSION (>{max_regression*100:.0f}%)"
            failures.append(
                f"{name}: branch {h['time']:.2f}s is {pct:+.1f}% vs base "
                f"{b['time']:.2f}s (allowed +{max_regression*100:.0f}%)"
            )
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

    widths = [max(len(headers[i]), *(len(r[i]) for r in rows)) for i in range(len(headers))]
    lines = [
        "## Latency compare (main vs branch)",
        "",
        f"- Base ref: `{base.get('ref_label', 'base')}` `{base.get('git_sha', '')}`",
        f"- Branch ref: `{branch.get('ref_label', 'branch')}` `{branch.get('git_sha', '')}`",
        f"- Limit: {base.get('limit')} / {branch.get('limit')}",
        f"- Total base: **{base.get('total_time', 0):.2f}s** · "
        f"Total branch: **{branch.get('total_time', 0):.2f}s**",
        f"- Max allowed regression: **{max_regression*100:.0f}%**",
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Base (main) JSON path")
    parser.add_argument("--branch", required=True, help="Branch JSON path")
    parser.add_argument(
        "--max-regression",
        type=float,
        default=float(os.environ.get("LATENCY_MAX_REGRESSION", "0.30")),
        help="Fail if branch is slower by this fraction (default 0.30 = 30%%)",
    )
    parser.add_argument(
        "--summary",
        default="",
        help="Optional path to write GitHub step summary markdown",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base = load(args.base)
    branch = load(args.branch)
    report, failures = compare(base, branch, args.max_regression)
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
        return 1
    print("No latency regressions beyond threshold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
