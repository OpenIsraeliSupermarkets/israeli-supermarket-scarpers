"""Weekly report of stability rules that approved "no files" while files came back.

The scraper tests emit ``STALE_STABILITY_RULE {json}`` (see
``ScraperStability.warn_if_files_found_when_empty_approved``). This script reads
the pytest logs of recent CI runs, groups the warnings by rule and request, and
writes a Markdown issue body. Standard library only, so the workflow needs no
install step.

Usage::

    python -m scripts.stale_stability_report \\
        --runs runs.json --logs-dir logs --out body.md

``runs.json`` is ``gh run list --json databaseId,createdAt,url`` output; each
run's log is ``<logs-dir>/<databaseId>/pytest-log.txt``. Prints the number of
distinct findings (0 means nothing to report).
"""

import argparse
import json
import os
import re
from collections import defaultdict

MARKER = "STALE_STABILITY_RULE"
# Payload is a flat JSON object (lists allowed, no nested objects).
_LINE_RE = re.compile(MARKER + r" (\{[^{}]*\})")


def parse_log(text):
    """Return the distinct warning payloads found in one log, as dicts.

    One run prints a warning twice or more (logger line, pytest summary,
    xdist), so payloads are de-duplicated per run.
    """
    seen = {}
    for match in _LINE_RE.finditer(text):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("scraper"):
            seen[json.dumps(payload, sort_keys=True)] = payload
    return list(seen.values())


def finding_key(payload):
    """Group by what the rule approved; the probe date changes every day."""
    files_types = payload.get("files_types")
    return (
        payload.get("scraper"),
        payload.get("rule"),
        ",".join(files_types) if files_types else "any",
        "yes" if payload.get("store_id") is not None else "no",
        "yes" if payload.get("when_date") else "no",
    )


def aggregate(runs):
    """``runs`` is ``[(run_dict, [payload, ...]), ...]``; return sorted findings."""
    grouped = defaultdict(lambda: {"runs": [], "max_files": 0})
    for run, payloads in runs:
        keys_in_run = set()
        for payload in payloads:
            key = finding_key(payload)
            entry = grouped[key]
            entry["max_files"] = max(entry["max_files"], payload.get("files_found", 0))
            if key not in keys_in_run:
                entry["runs"].append(run)
                keys_in_run.add(key)
    findings = [
        {
            "scraper": key[0],
            "rule": key[1],
            "files_types": key[2],
            "store_id": key[3],
            "when_date": key[4],
            "runs": entry["runs"],
            "max_files": entry["max_files"],
        }
        for key, entry in grouped.items()
    ]
    findings.sort(key=lambda f: (-len(f["runs"]), f["scraper"], f["files_types"]))
    return findings


def render(findings, runs_scanned, since):
    """Markdown issue body (without the fingerprint marker)."""
    lines = [
        f"Scheduled scraper tests since **{since}** ({runs_scanned} runs with a "
        "pytest log) got files back for requests that a `ScraperStability` rule "
        'approved as "no files". The rule may be stale: check the chain, then '
        "narrow or remove the rule in `il_supermarket_scarper/scraper_stability.py`.",
        "",
        "| Scraper | Rule | File types | Store id | Date filter | Runs with files | Max files |",
        "|---|---|---|---|---|---|---|",
    ]
    for f in findings:
        run_links = ", ".join(
            f"[{r.get('createdAt', '')[:10] or r.get('databaseId')}]({r.get('url')})"
            for r in f["runs"]
        )
        lines.append(
            f"| `{f['scraper']}` | `{f['rule']}` | {f['files_types']} | "
            f"{f['store_id']} | {f['when_date']} | "
            f"{len(f['runs'])}/{runs_scanned}: {run_links} | {f['max_files']} |"
        )
    lines += [
        "",
        "One run counts once per row. A rule seen in most runs is likely stale; "
        "one seen once may be a time-window edge.",
    ]
    return "\n".join(lines) + "\n"


def load_runs(runs_path, logs_dir):
    """Pair each run with the payloads in its downloaded log (skip runs without one)."""
    with open(runs_path, encoding="utf-8") as handle:
        runs = json.load(handle)
    paired = []
    for run in runs:
        path = os.path.join(logs_dir, str(run.get("databaseId")), "pytest-log.txt")
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8", errors="replace") as handle:
            paired.append((run, parse_log(handle.read())))
    return paired


def main(argv=None):
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", required=True)
    parser.add_argument("--logs-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--since", default="the last 7 days")
    args = parser.parse_args(argv)

    paired = load_runs(args.runs, args.logs_dir)
    findings = aggregate(paired)
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(render(findings, len(paired), args.since))
    print(len(findings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
