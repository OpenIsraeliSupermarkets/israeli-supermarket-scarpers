#!/usr/bin/env python3
"""Validate scraper list-only discovery against the human UI file listing.

Expectation: UI filenames ⊆ scraper collect_files_details_from_site.

UI inventory is collected by opening the portal and following per-scraper
element XPaths (``testing_util.ui_engine.UIEngine``) until the file table is populated — not by
reimplementing the scraper's listing logic.

Examples:
  python scripts/validate_ui_vs_scraper.py --scrapers BAREKET,KING_STORE
  python scripts/validate_ui_vs_scraper.py --configured-ui
  python scripts/validate_ui_vs_scraper.py --per-engine
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import sys
import tempfile
from collections import defaultdict
from datetime import timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin

import requests
from playwright.sync_api import sync_playwright

from il_supermarket_scarper.scrappers_factory import ScraperFactory
from il_supermarket_scarper.utils import DiskFileOutput, Logger, _now
from il_supermarket_scarper.utils.connection import collect_from_ftp
from il_supermarket_scarper.utils.databases import AbstractDataBase
from il_supermarket_scarper.utils.state import FilterState
from testing_util.ui_engine import (
    UI_DEFERRED,
    UIEngine,
    UiListingPath,
    configured_ui_scrapers,
)


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
    return candidates[0].rstrip("/").split("/")[-1]


def listed_factory_members() -> List[str]:
    """All enum members, including stability-disabled ones."""
    return [member.name for member in ScraperFactory]


def resolve_scrapers(args: argparse.Namespace) -> List[str]:
    """Resolve which scrapers to validate."""
    if args.scrapers:
        names = [name.strip() for name in args.scrapers.split(",") if name.strip()]
        skipped = [n for n in names if n in UI_DEFERRED]
        if skipped:
            print(f"Skipping deferred UI scrapers: {', '.join(skipped)}", flush=True)
        return [n for n in names if n not in UI_DEFERRED]
    if args.configured_ui:
        return configured_ui_scrapers()
    if args.all_listed:
        return listed_factory_members()
    if args.per_engine:
        by_engine: Dict[str, List[str]] = defaultdict(list)
        for name in listed_factory_members():
            cls = getattr(ScraperFactory, name).value
            by_engine[engine_name(cls)].append(name)
        return [names[0] for _, names in sorted(by_engine.items())]
    raise SystemExit("Specify --per-engine, --configured-ui, --all-listed, or --scrapers")


def make_scraper(enum_name: str):
    """Instantiate scraper class, bypassing ScraperFactory.get stability filter."""
    member = getattr(ScraperFactory, enum_name, None)
    if member is None:
        raise ValueError(f"Unknown scraper {enum_name}")
    return member.value, member


def ui_listing_url(scraper, path: UiListingPath) -> str:
    """Resolve human UI landing URL from scraper base + path."""
    base = getattr(scraper, "url", None)
    if not base:
        raise ValueError("scraper has no url for UI landing")
    if not path.landing_path:
        return base if base.endswith("/") else f"{base}/"
    return urljoin(base.rstrip("/") + "/", path.landing_path)


def _element_disabled(locator) -> bool:
    """True if Playwright considers the control non-clickable/disabled."""
    if locator.count() == 0:
        return True
    target = locator.first
    if target.is_disabled():
        return True
    class_name = target.get_attribute("class") or ""
    if "disabled" in class_name.lower():
        return True
    aria = target.get_attribute("aria-disabled")
    return aria == "true"


def _collect_names_from_page(page, file_name_xpath: str) -> Set[str]:
    texts = page.locator(f"xpath={file_name_xpath}").all_text_contents()
    return {norm_name(text) for text in texts if text and text.strip()}


def _wait_for_listing_change(page, file_name_xpath: str, before_url: str, before_first: str) -> bool:
    """Wait until URL or first filename cell changes after a pager click."""
    for _ in range(60):
        page.wait_for_timeout(250)
        if page.url != before_url:
            with contextlib.suppress(Exception):
                page.locator(f"xpath={file_name_xpath}").first.wait_for(
                    state="attached", timeout=15000
                )
            return True
        with contextlib.suppress(Exception):
            current_first = page.locator(f"xpath={file_name_xpath}").first.inner_text(
                timeout=1000
            )
            if current_first.strip() and current_first.strip() != before_first:
                return True
    return False


def _list_ui_via_clicks(landing_url: str, path: UiListingPath) -> Set[str]:
    """Open landing URL, apply selects/clicks, paginate, read filename cells."""
    names: Set[str] = set()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.goto(landing_url, timeout=90000, wait_until="domcontentloaded")

            # SPAs often paint an empty shell first; wait for either rows or controls.
            if path.file_name_xpath:
                with contextlib.suppress(Exception):
                    page.locator(f"xpath={path.file_name_xpath}").first.wait_for(
                        state="attached", timeout=60000
                    )

            for select_xpath, value in path.selects:
                page.locator(f"xpath={select_xpath}").first.select_option(value)
                page.wait_for_timeout(500)

            for xpath in path.clicks:
                click_target = page.locator(f"xpath={xpath}")
                click_target.first.wait_for(state="visible", timeout=60000)
                # Refresh buttons may stay disabled until the first fetch finishes.
                for _ in range(60):
                    if not _element_disabled(click_target):
                        break
                    page.wait_for_timeout(500)
                click_target.first.click(timeout=30000)
                page.wait_for_timeout(800)

            page.locator(f"xpath={path.file_name_xpath}").first.wait_for(
                state="attached", timeout=60000
            )
            page.wait_for_timeout(1000)

            for _ in range(500):  # hard cap on UI pages
                names |= _collect_names_from_page(page, path.file_name_xpath)
                if not path.next_page_xpath:
                    break
                next_btn = page.locator(f"xpath={path.next_page_xpath}")
                if _element_disabled(next_btn):
                    break
                before_url = page.url
                before_first = page.locator(f"xpath={path.file_name_xpath}").first.inner_text()
                next_btn.first.click(timeout=30000)
                if not _wait_for_listing_change(
                    page, path.file_name_xpath, before_url, before_first.strip()
                ):
                    break
        finally:
            browser.close()
    return names


async def _list_ui_ftp_names(scraper) -> Set[str]:
    names: Set[str] = set()
    extensions = getattr(scraper, "target_file_extensions", ("xml", "gz"))
    async for entry in collect_from_ftp(
        scraper.ftp_host,
        scraper.ftp_username,
        scraper.ftp_password or "",
        scraper.ftp_path,
        None,
    ):
        if not entry.name:
            continue
        if entry.name.split(".")[-1] not in extensions:
            continue
        names.add(norm_name(entry.name))
    return names


def _list_ui_http_json(landing_url: str, json_name_field: str) -> Set[str]:
    response = requests.get(landing_url, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list):
        return set()
    names: Set[str] = set()
    for entry in payload:
        if isinstance(entry, dict) and entry.get(json_name_field):
            names.add(norm_name(str(entry[json_name_field])))
    return names


async def _list_ui_wolt_daily(scraper, path: UiListingPath) -> Set[str]:
    names: Set[str] = set()
    base = scraper.url.rstrip("/")
    index_url = base if base.endswith("index.html") else f"{base}/index.html"
    for days_back in range(10):
        day = (_now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        landing = index_url.replace("index.html", f"{day}.html")
        names |= await asyncio.to_thread(_list_ui_via_clicks, landing, path)
    return names


async def list_ui_site_names(enum_name: str, scraper) -> Set[str]:
    """List filenames from the human UI via configured click XPaths."""
    try:
        path = UIEngine[enum_name].value
    except KeyError as exc:
        raise NotImplementedError(
            f"No UI click path defined for {enum_name}; add UIEngine.{enum_name}"
        ) from exc

    if path.inventory == "ftp":
        return await _list_ui_ftp_names(scraper)
    if path.inventory == "http_json":
        landing = ui_listing_url(scraper, path)
        return await asyncio.to_thread(
            _list_ui_http_json, landing, path.json_name_field
        )
    if path.inventory == "wolt_daily":
        return await _list_ui_wolt_daily(scraper, path)

    landing = ui_listing_url(scraper, path)
    return await asyncio.to_thread(_list_ui_via_clicks, landing, path)


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
        if enum_name in UIEngine.__members__:
            ui_path = UIEngine[enum_name].value
            meta["ui_inventory"] = ui_path.inventory
            if ui_path.inventory == "ftp":
                meta["ui_landing"] = getattr(scraper, "ftp_host", None)
            else:
                meta["ui_landing"] = ui_listing_url(scraper, ui_path)
            meta["ui_clicks"] = list(ui_path.clicks)
        names: Set[str] = set()
        async for first, second in scraper.collect_files_details_from_site(
            FilterState(), limit=None
        ):
            filename = pick_filename(first, second)
            if filename:
                names.add(norm_name(filename))
    return names, meta


async def validate_one(enum_name: str) -> Dict[str, Any]:
    """Compare site vs scraper for one factory member."""
    row: Dict[str, Any] = {"scraper": enum_name}
    if enum_name in UI_DEFERRED:
        row["skipped"] = True
        row["skip_reason"] = "UI path deferred"
        row["pass"] = True
        return row
    if enum_name not in UIEngine.__members__:
        row["skipped"] = True
        row["skip_reason"] = "No UIEngine entry"
        row["pass"] = True
        return row
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
            site_set = await list_ui_site_names(enum_name, scraper)
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
        if row.get("skipped"):
            print(f"  SKIP {row.get('skip_reason')}", flush=True)
            results.append(row)
            continue
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
        "--configured-ui",
        action="store_true",
        help="Every scraper with a UIEngine path (excludes UI_DEFERRED)",
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
