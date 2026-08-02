#!/usr/bin/env python3
"""Validate that scraper list-only discovery retrieves every UI/site file.

Expectation: UI/site file set ⊆ scraper collect_files_details_from_site set.

Instantiates scrapers via ``ScraperFactory.<NAME>.value`` (bypasses stability
filters). Use ``--per-engine`` for one sample per engine, or ``--scrapers`` /
``--all-listed`` for explicit coverage.

Examples:
  python scripts/validate_ui_vs_scraper.py --per-engine
  python scripts/validate_ui_vs_scraper.py --scrapers BAREKET,TIV_TAAM
  python scripts/validate_ui_vs_scraper.py --all-listed --output report.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from il_supermarket_scarper.engines import (
    ApiWebEngine,
    Bina,
    Cerberus,
    MultiPageWeb,
    PublishPrice,
)
from il_supermarket_scarper.engines.matrix import Matrix
from il_supermarket_scarper.engines.web import WebBase
from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import DiskFileOutput, FileEntry, Logger
from il_supermarket_scarper.utils.connection import collect_from_ftp
from il_supermarket_scarper.utils.databases import AbstractDataBase
from il_supermarket_scarper.utils.state import FilterState
from il_supermarket_scarper.utils.status import _now




class NoOpStatusDatabase(AbstractDataBase):
    """In-memory status DB so prior downloads never shrink listings."""

    def __init__(self, database_name):
        super().__init__(database_name)
        self._data: Dict[str, Any] = {}

    def insert_document(self, collection_name, document):
        self._data.setdefault(collection_name, []).append(document)
        self._update_last_modified()

    def insert_documents(self, collection_name, document):
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


def engine_name(cls) -> str:
    """Best-effort engine label from MRO."""
    return cls.__name__


def norm_name(name: Optional[str]) -> str:
    """Collapse UI/scraper naming quirks (e.g. cell 'x.gz' + scraper '.xml.gz')."""
    value = (name or "").strip().split("/")[-1].lower()
    while True:
        previous = value
        for suffix in (".xml.gz", ".gz", ".xml", ".zip"):
            if value.endswith(suffix):
                value = value[: -len(suffix)]
                break
        if value == previous:
            break
    return value


def pick_filename(first: Any, second: Any) -> Optional[str]:
    """Normalize collect_files_details yield order.

    Web engines yield ``(url, name)``; Cerberus yields ``(name, url)``.
    """
    candidates = []
    for item in (first, second):
        if isinstance(item, str) and item.strip():
            candidates.append(item.strip())
    if not candidates:
        return None
    for item in candidates:
        if item.startswith("http://") or item.startswith("https://"):
            continue
        return item
    # fall back to basename of URL
    return candidates[0].rstrip("/").split("/")[-1]


def listed_factory_members() -> List[str]:
    """All enum members, including stability-disabled ones."""
    return [member.name for member in ScraperFactory]


def resolve_scrapers(args: argparse.Namespace) -> List[str]:
    """Resolve which scrapers to validate."""
    if args.scrapers:
        return [name.strip() for name in args.scrapers.split(",") if name.strip()]
    if args.all_listed:
        return listed_factory_members()
    if args.per_engine:
        by_engine: Dict[str, List[str]] = defaultdict(list)
        for name in listed_factory_members():
            cls = getattr(ScraperFactory, name).value
            by_engine[engine_name(cls)].append(name)
        chosen = []
        for eng, names in sorted(by_engine.items()):
            chosen.append(names[0])
        return chosen
    raise SystemExit("Specify --per-engine, --all-listed, or --scrapers")


def make_scraper(enum_name: str):
    """Instantiate scraper class, bypassing ScraperFactory.get stability filter."""
    member = getattr(ScraperFactory, enum_name, None)
    if member is None:
        raise ValueError(f"Unknown scraper {enum_name}")
    return member.value, member


async def list_scraper_names(enum_name: str) -> Tuple[Set[str], Dict[str, Any]]:
    """Drain collect_files_details_from_site (no download)."""
    cls, member = make_scraper(enum_name)
    meta: Dict[str, Any] = {
        "engine": engine_name(cls),
        "class": cls.__name__,
        "enabled_by_factory": ScraperFactory.is_scraper_enabled(member),
    }
    status_db = NoOpStatusDatabase(database_name=enum_name)
    with tempfile.TemporaryDirectory(prefix=f"val_{enum_name}_") as tmp:
        scraper = cls(
            file_output=DiskFileOutput(storage_path=tmp),
            status_database=status_db,
        )
        meta["url"] = getattr(scraper, "url", None) or getattr(
            scraper, "ftp_host", None
        )
        names: Set[str] = set()
        async for first, second in scraper.collect_files_details_from_site(
            FilterState(), limit=None
        ):
            filename = pick_filename(first, second)
            if filename:
                names.add(norm_name(filename))
    return names, meta


async def site_names_publishprice(scraper) -> Set[str]:
    response = requests.get(scraper.url, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    script = soup.find_all("script")[-2].text
    files = json.loads(
        script.split("const files = ")[1].split("\n")[0].replace(";", "")
    )
    return {norm_name(entry["name"]) for entry in files}


async def site_names_bina(scraper) -> Set[str]:
    names: Set[str] = set()
    for chain_id in scraper.get_chain_id():
        params = {
            "_": chain_id,
            "wReshet": "הכל",
            "WFileType": "0",
            "WDate": "",
            "WStore": "",
        }
        url = scraper.url.rstrip("/") + "/" + scraper.aspx_page + "?" + urlencode(params)
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            continue
        for entry in data:
            if isinstance(entry, dict) and entry.get("FileNm"):
                names.add(norm_name(entry["FileNm"]))
    return names


async def site_names_matrix(scraper) -> Set[str]:
    url = scraper.url.rstrip("/") + "/" + scraper.aspx_page
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    names: Set[str] = set()
    hebrew = getattr(scraper, "chain_hebrew_name", None)
    for row in soup.find_all("tr")[1:]:
        text = str(row)
        if hebrew and hebrew not in text:
            continue
        link = row.find("a")
        if not link or not link.get("href"):
            continue
        names.add(norm_name(link["href"]))
    return names


async def site_names_apiweb(scraper) -> Set[str]:
    """Hit the same /webapi endpoints the SPA uses (deduped by fileName)."""
    session = requests.Session()
    base = scraper.url.rstrip("/")
    names: Set[str] = set()
    for edi in scraper.get_chain_id():
        branches_resp = session.get(
            f"{base}/webapi/api/getbranches", params={"edi": edi}, timeout=60
        )
        if branches_resp.status_code >= 400:
            continue
        branches = branches_resp.json()
        if not isinstance(branches, list) or not branches:
            continue
        for branch in branches:
            if not isinstance(branch, dict):
                continue
            params = {"edi": edi, "branchNumber": branch.get("number")}
            files_resp = session.get(
                f"{base}/webapi/api/getfiles", params=params, timeout=60
            )
            data = files_resp.json()
            if not isinstance(data, list):
                continue
            for entry in data:
                if isinstance(entry, dict) and entry.get("fileName"):
                    names.add(norm_name(entry["fileName"]))
    return names


async def site_names_cerberus(scraper) -> Set[str]:
    names: Set[str] = set()
    async for entry in collect_from_ftp(
        scraper.ftp_host,
        scraper.ftp_username,
        scraper.ftp_password or "",
        scraper.ftp_path,
        None,
    ):
        if not entry.name:
            continue
        if entry.name.split(".")[-1] not in getattr(
            scraper, "target_file_extensions", ("xml", "gz")
        ):
            continue
        names.add(norm_name(entry.name))
    return names


async def site_names_via_generate_all_files(scraper) -> Set[str]:
    """Page/HTML inventory via the engine's raw listing generator."""
    names: Set[str] = set()
    listing = scraper.generate_all_files()
    try:
        async for entry in listing:
            if isinstance(entry, FileEntry):
                names.add(norm_name(entry.name))
            elif isinstance(entry, (tuple, list)) and entry:
                names.add(norm_name(str(entry[0])))
            else:
                names.add(norm_name(str(entry)))
    finally:
        await listing.aclose()
    return names


async def list_site_names(scraper) -> Set[str]:
    """Independent site/UI inventory for the scraper's engine family."""
    if isinstance(scraper, PublishPrice):
        return await site_names_publishprice(scraper)
    if isinstance(scraper, Bina):
        return await site_names_bina(scraper)
    if isinstance(scraper, Matrix):
        return await site_names_matrix(scraper)
    if isinstance(scraper, ApiWebEngine):
        return await site_names_apiweb(scraper)
    if isinstance(scraper, Cerberus):
        return await site_names_cerberus(scraper)
    if isinstance(scraper, (MultiPageWeb, WebBase)):
        return await site_names_via_generate_all_files(scraper)
    raise TypeError(f"No site lister for {type(scraper).__name__}")


async def validate_one(enum_name: str) -> Dict[str, Any]:
    """Compare site vs scraper for one factory member."""
    row: Dict[str, Any] = {"scraper": enum_name}
    try:
        scraper_set, meta = await list_scraper_names(enum_name)
        row.update(meta)
        row["scraper_count"] = len(scraper_set)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        row["error_scraper"] = str(exc)
        row["pass"] = False
        return row

    try:
        cls, _member = make_scraper(enum_name)
        with tempfile.TemporaryDirectory(prefix=f"site_{enum_name}_") as tmp:
            scraper = cls(
                file_output=DiskFileOutput(storage_path=tmp),
                status_database=NoOpStatusDatabase(database_name=f"site_{enum_name}"),
            )
            site_set = await list_site_names(scraper)
        row["ui_count"] = len(site_set)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        row["error_ui"] = str(exc)
        row["pass"] = False
        return row

    missing = sorted(site_set - scraper_set)
    extra = sorted(scraper_set - site_set)
    row["ui_not_in_scraper"] = len(missing)
    row["scraper_not_in_ui"] = len(extra)
    row["missing_sample"] = missing[:15]
    row["extra_sample"] = extra[:15]
    row["pass"] = len(missing) == 0
    return row


async def run(scrapers: List[str]) -> List[Dict[str, Any]]:
    Logger.set_logging_level(os.environ.get("VALIDATE_LOG_LEVEL", "ERROR"))
    results = []
    for name in scrapers:
        print(f"Validating {name}...", flush=True)
        row = await validate_one(name)
        status = "PASS" if row.get("pass") else "FAIL"
        print(
            f"  {status} engine={row.get('engine')} "
            f"ui={row.get('ui_count')} scraper={row.get('scraper_count')} "
            f"missing={row.get('ui_not_in_scraper')} "
            f"error={row.get('error_scraper') or row.get('error_ui')}",
            flush=True,
        )
        results.append(row)
    return results


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
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
        "--output",
        default="scripts/validation_ui_vs_scraper.json",
        help="JSON report path (default: scripts/validation_ui_vs_scraper.json)",
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        default=True,
        help="Exit 1 if any UI file is missing from scraper (default)",
    )
    parser.add_argument(
        "--no-fail-on-missing",
        action="store_false",
        dest="fail_on_missing",
        help="Always exit 0 after writing the report",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    scrapers = resolve_scrapers(args)
    results = asyncio.run(run(scrapers))
    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, ensure_ascii=False)
    print(f"Wrote {args.output}", flush=True)

    failed = [row for row in results if not row.get("pass")]
    if args.fail_on_missing and failed:
        print(f"{len(failed)} scraper(s) failed UI⊆scraper check", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
