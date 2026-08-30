"""Human UI navigation paths for UI ⊆ scraper validation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Literal, Optional, Tuple

InventoryKind = Literal["browser", "ftp", "http_json", "wolt_daily", "hazi_hinam"]

_PAGINATION_NEXT_LI = (
    "//li[contains(concat(' ', normalize-space(@class), ' '), ' pagination-item ') "
    "and contains(concat(' ', normalize-space(@class), ' '), ' is-active ')]"
    "/following-sibling::li[contains(concat(' ', normalize-space(@class), ' '), "
    "' pagination-item ')][1]/a"
)


@dataclass(frozen=True)
class UiListingPath:  # pylint: disable=too-many-instance-attributes
    """How to reach the human-visible file listing for a scraper.

    ``inventory``:
      - ``browser``: Playwright + ``clicks`` / ``file_name_xpath`` (and optional pager).
      - ``ftp``: Cerberus — directory listing via FTP (no HTML UI).
      - ``http_json``: single GET to ``landing_path`` / scraper URL; JSON array field
        ``json_name_field``.
      - ``wolt_daily``: last 10 day HTML pages under ``…/YYYY-MM-DD.html``.
      - ``hazi_hinam``: Hazi Hinam — pagination links drop date; walk ``?p=N&d=`` pages.
    """

    clicks: Tuple[str, ...]
    file_name_xpath: str
    landing_path: str = ""
    selects: Tuple[Tuple[str, str], ...] = ()
    next_page_xpath: Optional[str] = None
    key: str = ""  # must match ScraperFactory member name
    inventory: InventoryKind = "browser"
    json_name_field: str = "name"


# Optional: scrapers with a registry entry but validation disabled (flaky/slow).
UI_DEFERRED: frozenset[str] = frozenset()


def _bina_main_ui(scraper_key: str) -> UiListingPath:
    return UiListingPath(
        key=scraper_key,
        landing_path="Main.aspx",
        clicks=('//*[@id="Button1"]',),
        file_name_xpath='//*[@id="myTable"]//tr[td]/td[1]',
    )


def _laibcatalog_spa_ui(scraper_key: str, landing_path: str) -> UiListingPath:
    return UiListingPath(
        key=scraper_key,
        landing_path=landing_path,
        selects=(('//*[@id="pageSize"]', "100"),),
        clicks=('//*[@id="btnRefresh"]',),
        file_name_xpath='//*[@id="filesBody"]/tr/td[2]',
        next_page_xpath='//*[@id="btnNext" and not(@disabled)]',
    )


def _publishprice_spa_ui(scraper_key: str) -> UiListingPath:
    return UiListingPath(
        key=scraper_key,
        landing_path="",
        clicks=(),
        file_name_xpath="//a[contains(concat(' ', normalize-space(@class), ' '), ' fileNameA ')]",
        next_page_xpath=(
            "//div[contains(concat(' ', normalize-space(@class), ' '), ' paginationDiv ')]"
            "/div[contains(concat(' ', normalize-space(@class), ' '), ' paginationPages ')]"
            "/following-sibling::button[contains(concat(' ', normalize-space(@class), ' '), "
            "' paginationNav ') and not(contains(concat(' ', normalize-space(@class), ' '), "
            "' paginationBtn_disabled '))][1]"
        ),
    )


def _striped_table_ui(scraper_key: str, landing_path: str = "") -> UiListingPath:
    """MultiPageWeb sites with Bootstrap striped tables (Hazi Hinam, City Market Shops)."""
    return UiListingPath(
        key=scraper_key,
        landing_path=landing_path,
        clicks=(),
        file_name_xpath="//table[contains(@class,'table-striped')]/tbody/tr/td[3]",
        next_page_xpath=_PAGINATION_NEXT_LI,
    )


def _cerberus_ftp_ui(scraper_key: str) -> UiListingPath:
    return UiListingPath(
        key=scraper_key,
        inventory="ftp",
        clicks=(),
        file_name_xpath="",
    )


class UIEngine(Enum):
    """Per ScraperFactory member: path to the human file listing."""

    # --- Bina (Main.aspx) ---
    BAREKET = _bina_main_ui("BAREKET")
    GOOD_PHARM = _bina_main_ui("GOOD_PHARM")
    KING_STORE = _bina_main_ui("KING_STORE")
    MAAYAN_2000 = _bina_main_ui("MAAYAN_2000")
    SUPER_SAPIR = _bina_main_ui("SUPER_SAPIR")
    SHUK_AHIR = _bina_main_ui("SHUK_AHIR")
    SHEFA_BARCART_ASHEM = _bina_main_ui("SHEFA_BARCART_ASHEM")
    ZOL_VEBEGADOL = _bina_main_ui("ZOL_VEBEGADOL")
    CITY_MARKET_KIRYATGAT = _bina_main_ui("CITY_MARKET_KIRYATGAT")
    MESHMAT_YOSEF_2 = _bina_main_ui("MESHMAT_YOSEF_2")

    # --- MultiPageWeb ---
    SHUFERSAL = UiListingPath(
        key="SHUFERSAL",
        landing_path="",
        clicks=(),
        file_name_xpath='//*[@id="gridContainer"]/table/tbody/tr/td[7]',
        next_page_xpath='//*[@id="gridContainer"]/table/tfoot//a[normalize-space()=">"]',
    )
    SUPER_PHARM = UiListingPath(
        key="SUPER_PHARM",
        landing_path="",
        clicks=(),
        file_name_xpath="//table[contains(@class,'gzTable')]//tbody/tr/td[2]",
        next_page_xpath=(
            '//*[@class="mvc-grid-pager"]'
            '/button[normalize-space()="›" and not(@disabled)]'
        ),
    )
    CITY_MARKET_SHOPS = _striped_table_ui("CITY_MARKET_SHOPS")
    # Pagination links drop the date query param; validate_ui_vs_scraper walks pages via URL.
    HAZI_HINAM = UiListingPath(
        key="HAZI_HINAM",
        inventory="hazi_hinam",
        clicks=(),
        file_name_xpath="//table[contains(@class,'table-striped')]/tbody/tr/td[3]",
    )

    # --- PublishPrice SPA ---
    YAYNO_BITAN_AND_CARREFOUR = _publishprice_spa_ui("YAYNO_BITAN_AND_CARREFOUR")
    # QUIK = _publishprice_spa_ui("QUIK")  # disabled with ScraperFactory.QUIK

    # --- laibcatalog SPAs ---
    VICTORY_NEW_SOURCE = _laibcatalog_spa_ui("VICTORY_NEW_SOURCE", "victory/index.html")
    HET_COHEN_NEW_SOURCE = _laibcatalog_spa_ui(
        "HET_COHEN_NEW_SOURCE", "hcohen/index.html"
    )
    MAHSANI_ASHUK_NEW_SOURCE = _laibcatalog_spa_ui(
        "MAHSANI_ASHUK_NEW_SOURCE", "mshuk/index.html"
    )

    # --- WebBase / other HTTP ---
    NETIV_HASED = UiListingPath(
        key="NETIV_HASED",
        landing_path="",
        clicks=(),
        file_name_xpath="//table/tbody/tr/td[6]",
    )
    MESHMAT_YOSEF_1 = UiListingPath(
        key="MESHMAT_YOSEF_1",
        inventory="http_json",
        clicks=(),
        file_name_xpath="",
        json_name_field="name",
    )
    WOLT = UiListingPath(
        key="WOLT",
        inventory="wolt_daily",
        landing_path="",
        clicks=(),
        file_name_xpath="//li[.//a]",
    )

    # --- Cerberus (FTP directory listing; no browser UI) ---
    # COFIX = _cerberus_ftp_ui("COFIX")  # disabled with ScraperFactory.COFIX
    DOR_ALON = _cerberus_ftp_ui("DOR_ALON")
    KESHET = _cerberus_ftp_ui("KESHET")
    OSHER_AD = _cerberus_ftp_ui("OSHER_AD")
    POLIZER = _cerberus_ftp_ui("POLIZER")
    RAMI_LEVY = _cerberus_ftp_ui("RAMI_LEVY")
    SALACH_DABACH = _cerberus_ftp_ui("SALACH_DABACH")
    STOP_MARKET = _cerberus_ftp_ui("STOP_MARKET")
    SUPER_YUDA = _cerberus_ftp_ui("SUPER_YUDA")
    FRESH_MARKET_AND_SUPER_DOSH = _cerberus_ftp_ui("FRESH_MARKET_AND_SUPER_DOSH")
    TIV_TAAM = _cerberus_ftp_ui("TIV_TAAM")
    YELLOW = _cerberus_ftp_ui("YELLOW")
    YOHANANOF = _cerberus_ftp_ui("YOHANANOF")


def configured_ui_scrapers() -> List[str]:
    """ScraperFactory names that have a UIEngine path and are not deferred."""
    return sorted(n for n in UIEngine.__members__ if n not in UI_DEFERRED)


def factory_scrapers() -> List[str]:
    """All listed ScraperFactory enum names (import here to avoid circular imports in tests)."""
    # Local import keeps testing_util usable without pulling the full package graph.
    from il_supermarket_scarper.scrappers_factory import (  # pylint: disable=import-outside-toplevel
        ScraperFactory,
    )

    return ScraperFactory.all_listed_scrappers()
