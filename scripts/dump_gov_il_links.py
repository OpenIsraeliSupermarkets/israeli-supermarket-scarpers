#!/usr/bin/env python3
"""Dump retailer portal links for CPFTA chains.

Tries the live gov.il page first. Outside Israel this often returns Cloudflare
403 — in that case write the skill fallback URL table so agents still have a
single JSON map without re-browsing.

  python scripts/dump_gov_il_links.py --output scripts/gov_il_links.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


def _is_skipped_host(href: str) -> bool:
    """True for gov.il / Cloudflare hosts (ignore path/query substrings)."""
    host = (urlparse(href).hostname or "").lower()
    if not host:
        return True
    return (
        host == "gov.il"
        or host.endswith(".gov.il")
        or host == "cloudflare.com"
        or host.endswith(".cloudflare.com")
    )


GOV_IL_URLS = (
    "https://www.gov.il/he/departments/legalInfo/cpfta_prices_regulations",
    "https://www.gov.il/he/pages/cpfta_prices_regulations",
)

# Mirrors .cursor/skills/inspect-supermarket-sites/SKILL.md (web + FTP).
SKILL_FALLBACK_LINKS: List[Dict[str, Any]] = [
    {
        "scraper": "BAREKET",
        "hebrew": "עוף והודו ברקת",
        "engine": "Bina",
        "href": "http://superbareket.binaprojects.com/MainIO_Hok.aspx",
    },
    {
        "scraper": "CITY_MARKET_KIRYATGAT",
        "hebrew": "סיטי מרקט",
        "engine": "Bina",
        "href": "http://citymarketkiryatgat.binaprojects.com/MainIO_Hok.aspx",
    },
    {
        "scraper": "CITY_MARKET_SHOPS",
        "hebrew": "סיטי מרקט",
        "engine": "MultiPageWeb",
        "href": "http://www.citymarket-shops.co.il/",
    },
    {
        "scraper": "GOOD_PHARM",
        "hebrew": "גוד פארם",
        "engine": "Bina",
        "href": "http://goodpharm.binaprojects.com/MainIO_Hok.aspx",
    },
    {
        "scraper": "HAZI_HINAM",
        "hebrew": "כל בו חצי חינם",
        "engine": "MultiPageWeb",
        "href": "https://shop.hazi-hinam.co.il/Prices",
    },
    {
        "scraper": "HET_COHEN_NEW_SOURCE",
        "hebrew": "ח. כהן",
        "engine": "ApiWeb",
        "href": "https://laibcatalog.co.il/hcohen/index.html",
    },
    {
        "scraper": "KING_STORE",
        "hebrew": "אלמשהדאוי קינג סטור",
        "engine": "Bina",
        "href": "http://kingstore.binaprojects.com/MainIO_Hok.aspx",
    },
    {
        "scraper": "MAAYAN_2000",
        "hebrew": "מעיין אלפיים",
        "engine": "Bina",
        "href": "http://maayan2000.binaprojects.com/MainIO_Hok.aspx",
    },
    {
        "scraper": "MAHSANI_ASHUK_NEW_SOURCE",
        "hebrew": "מחסני השוק",
        "engine": "ApiWeb",
        "href": "https://laibcatalog.co.il/mshuk/index.html",
    },
    {
        "scraper": "MESHMAT_YOSEF_1",
        "hebrew": "משנת יוסף",
        "engine": "WebBase",
        "href": "https://list-files.w5871031-kt.workers.dev/",
    },
    {
        "scraper": "NETIV_HASED",
        "hebrew": "נתיב החסד",
        "engine": "WebBase",
        "href": "https://app.netiv-hesed.com/",
    },
    {
        "scraper": "QUIK",
        "hebrew": "קוויק",
        "engine": "PublishPrice",
        "href": "https://prices.quik.co.il/",
    },
    {
        "scraper": "SHEFA_BARCART_ASHEM",
        "hebrew": "שפע ברכת השם",
        "engine": "Bina",
        "href": "http://shefabirkathashem.binaprojects.com/MainIO_Hok.aspx",
    },
    {
        "scraper": "SHUFERSAL",
        "hebrew": "שופרסל",
        "engine": "MultiPageWeb",
        "href": "https://prices.shufersal.co.il/",
    },
    {
        "scraper": "SHUK_AHIR",
        "hebrew": "שוק העיר",
        "engine": "Bina",
        "href": "http://shuk-hayir.binaprojects.com/MainIO_Hok.aspx",
    },
    {
        "scraper": "SUPER_PHARM",
        "hebrew": "סופר פארם",
        "engine": "MultiPageWeb",
        "href": "http://prices.super-pharm.co.il/",
    },
    {
        "scraper": "SUPER_SAPIR",
        "hebrew": "סופר ספיר",
        "engine": "Bina",
        "href": "http://supersapir.binaprojects.com/MainIO_Hok.aspx",
    },
    {
        "scraper": "VICTORY_NEW_SOURCE",
        "hebrew": "ויקטורי",
        "engine": "ApiWeb",
        "href": "https://laibcatalog.co.il/victory/index.html",
    },
    {
        "scraper": "WOLT",
        "hebrew": "וולט",
        "engine": "WebBase",
        "href": "https://wm-gateway.wolt.com/isr-prices/public/v1/index.html",
    },
    {
        "scraper": "YAYNO_BITAN_AND_CARREFOUR",
        "hebrew": "יינות ביתן / קרפור",
        "engine": "PublishPrice",
        "href": "https://prices.carrefour.co.il/",
    },
    {
        "scraper": "ZOL_VEBEGADOL",
        "hebrew": "זול ובגדול",
        "engine": "Bina",
        "href": "http://zolvebegadol.binaprojects.com/MainIO_Hok.aspx",
    },
    # Cerberus / FTP
    {
        "scraper": "COFIX",
        "hebrew": "קופיקס",
        "engine": "Cerberus",
        "href": "ftp://url.retail.publishedprices.co.il/",
        "ftp_user": "SuperCofixApp",
        "ftp_path": "/",
    },
    {
        "scraper": "DOR_ALON",
        "hebrew": "דור אלון",
        "engine": "Cerberus",
        "href": "ftp://url.retail.publishedprices.co.il/",
        "ftp_user": "doralon",
        "ftp_path": "/",
    },
    {
        "scraper": "FRESH_MARKET_AND_SUPER_DOSH",
        "hebrew": "פרשמרקט",
        "engine": "Cerberus",
        "href": "ftp://url.retail.publishedprices.co.il/",
        "ftp_user": "freshmarket",
        "ftp_path": "/",
    },
    {
        "scraper": "KESHET",
        "hebrew": "קשת טעמים",
        "engine": "Cerberus",
        "href": "ftp://url.retail.publishedprices.co.il/",
        "ftp_user": "Keshet",
        "ftp_path": "/",
    },
    {
        "scraper": "OSHER_AD",
        "hebrew": "אושר עד",
        "engine": "Cerberus",
        "href": "ftp://url.retail.publishedprices.co.il/",
        "ftp_user": "osherad",
        "ftp_path": "/",
    },
    {
        "scraper": "POLIZER",
        "hebrew": "פוליצר",
        "engine": "Cerberus",
        "href": "ftp://url.retail.publishedprices.co.il/",
        "ftp_user": "politzer",
        "ftp_path": "/",
    },
    {
        "scraper": "RAMI_LEVY",
        "hebrew": "רמי לוי",
        "engine": "Cerberus",
        "href": "ftp://url.retail.publishedprices.co.il/",
        "ftp_user": "RamiLevi",
        "ftp_path": "/",
    },
    {
        "scraper": "SALACH_DABACH",
        "hebrew": "סאלח דבאח",
        "engine": "Cerberus",
        "href": "ftp://url.retail.publishedprices.co.il/",
        "ftp_user": "SalachD",
        "ftp_path": "/",
    },
    {
        "scraper": "STOP_MARKET",
        "hebrew": "סטופ מרקט",
        "engine": "Cerberus",
        "href": "ftp://url.retail.publishedprices.co.il/",
        "ftp_user": "Stop_Market",
        "ftp_path": "/",
    },
    {
        "scraper": "SUPER_YUDA",
        "hebrew": "סופר יודה",
        "engine": "Cerberus",
        "href": "ftp://url.retail.publishedprices.co.il/",
        "ftp_user": "yuda_ho",
        "ftp_path": "/Yuda",
    },
    {
        "scraper": "TIV_TAAM",
        "hebrew": "טיב טעם",
        "engine": "Cerberus",
        "href": "ftp://url.retail.publishedprices.co.il/",
        "ftp_user": "TivTaam",
        "ftp_path": "/",
    },
    {
        "scraper": "YELLOW",
        "hebrew": "יילו",
        "engine": "Cerberus",
        "href": "ftp://url.retail.publishedprices.co.il/",
        "ftp_user": "Paz_bo",
        "ftp_path": "/",
    },
    {
        "scraper": "YOHANANOF",
        "hebrew": "יוחננוף",
        "engine": "Cerberus",
        "href": "ftp://url.retail.publishedprices.co.il/",
        "ftp_user": "yohananof",
        "ftp_path": "/",
    },
]


def fetch_html(url: str) -> str:
    """Fetch a gov.il page, rejecting Cloudflare/blocked responses."""
    response = requests.get(
        url,
        timeout=60,
        headers={"User-Agent": "Mozilla/5.0 (compatible; il-supermarket-scarper/1.0)"},
    )
    if response.status_code in (401, 403, 503):
        raise PermissionError(f"{response.status_code} from {url}")
    response.raise_for_status()
    text = response.text
    if "cloudflare" in text.lower() and "binaprojects" not in text.lower():
        raise PermissionError(f"Cloudflare/challenge page from {url}")
    return text


def fetch_via_content_api() -> str:
    """Fetch CPFTA HTML via the public gov.il content API (bypasses Cloudflare)."""
    # Local import: dump script also runs as a standalone helper.
    from il_supermarket_scarper.utils.connection import (  # pylint: disable=import-outside-toplevel
        _fetch_gov_il_content_api,
        _gov_il_api_to_html,
    )

    return _gov_il_api_to_html(_fetch_gov_il_content_api("cpfta_prices_regulations"))


def extract_links(html: str, page_url: str) -> List[Dict[str, Any]]:
    """Extract external retailer portal links from a CPFTA HTML page."""
    soup = BeautifulSoup(html, "lxml")
    rows: List[Dict[str, Any]] = []
    seen = set()
    for anchor in soup.find_all("a", href=True) or []:
        href = anchor["href"].strip()
        text = " ".join(anchor.get_text(" ", strip=True).split())
        if not href.startswith("http"):
            continue
        if _is_skipped_host(href):
            continue
        key = (text, href)
        if key in seen:
            continue
        seen.add(key)
        context = text
        parent = anchor.parent
        for _ in range(6):
            if parent is None:
                break
            blob = " ".join(parent.get_text(" ", strip=True).split())
            if 5 < len(blob) < 240:
                context = blob
                break
            parent = parent.parent
        rows.append(
            {
                "link_text": text,
                "href": href,
                "context": context,
                "source_page": page_url,
            }
        )
    return rows


def parse_args():
    """Parse CLI arguments for dumping gov.il retailer links."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="scripts/gov_il_links.json",
        help="JSON output path",
    )
    parser.add_argument(
        "--fallback-only",
        action="store_true",
        help="Skip live gov.il fetch; write skill URL table only",
    )
    return parser.parse_args()


def main() -> int:
    """Fetch or fall back and write the retailer links JSON map."""
    args = parse_args()
    errors: List[str] = []
    links: Optional[List[Dict[str, Any]]] = None
    source = "skill_fallback"

    if not args.fallback_only:
        for url in GOV_IL_URLS:
            try:
                html = fetch_html(url)
                extracted = extract_links(html, url)
                if not extracted:
                    errors.append(f"{url}: fetched but 0 retailer links")
                    continue
                links = extracted
                source = url
                break
            except Exception as exc:  # pylint: disable=broad-exception-caught
                errors.append(f"{url}: {exc}")

        if links is None:
            try:
                html = fetch_via_content_api()
                extracted = extract_links(
                    html, "https://www.gov.il/he/pages/cpfta_prices_regulations"
                )
                if extracted:
                    links = extracted
                    source = "gov.il_content_api"
                else:
                    errors.append("content API: fetched but 0 retailer links")
            except Exception as exc:  # pylint: disable=broad-exception-caught
                errors.append(f"content API: {exc}")

    if links is None:
        links = list(SKILL_FALLBACK_LINKS)
        source = "skill_fallback"
        print(
            "gov.il unavailable or empty; writing skill fallback table",
            flush=True,
        )

    payload = {
        "source": source,
        "count": len(links),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "links": links,
        "errors": errors,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    print(f"Wrote {args.output} ({len(links)} links, source={source})", flush=True)
    # Exit 0 even on fallback — callers still get a usable map.
    # Exit 3 only if somehow empty.
    return 0 if links else 3


if __name__ == "__main__":
    sys.exit(main())
