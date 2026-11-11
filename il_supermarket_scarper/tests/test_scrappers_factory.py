import tempfile
import unittest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import requests

import il_supermarket_scarper
from il_supermarket_scarper import ScraperStability, ScraperFactory, datetime_in_tlv
from il_supermarket_scarper.scraper_stability import (
    DoNotPublishPromo,
    MeshnatYosef1WorkerOutage,
    ScraperKind,
)
from il_supermarket_scarper.scrappers.nativ_hashed import NetivHased
from il_supermarket_scarper.utils.scraping.deprecated_scrapers import DeprecatedScrapers
from il_supermarket_scarper.utils.files.file_types import FileTypesFilters
from il_supermarket_scarper.utils.scraping.folders_name import DumpFolderNames
from il_supermarket_scarper.utils.scraping.status import get_cpfta_retailer_hosts, href_host
from il_supermarket_scarper.utils.files.file_output import DiskFileOutput


def test_scraper_stability_is_a_public_import():
    """Customers check an empty listing via the package root."""
    assert il_supermarket_scarper.ScraperStability is ScraperStability
    assert callable(ScraperStability.is_validate_scraper_found_no_files)


def test_stable_scraper():
    """test sample stable scarper"""
    assert not ScraperStability.is_validate_scraper_found_no_files(
        ScraperFactory.BAREKET.name
    )


def test_listed_scrapers_stay_enabled():
    """Every non-deprecated scraper is active, including always-failing ones."""
    listed = set(ScraperFactory.all_listed_scrappers())
    assert set(ScraperFactory.all_scrapers_name()) == listed
    for name in ScraperStability.get_always_failing_scrapers():
        assert ScraperFactory.is_scraper_enabled(ScraperFactory[name])


def test_scraper_kinds():
    """Three kinds: edge-case, always-failing (still on gov.il), deprecated."""
    assert set(ScraperStability.get_deprecated_scrapers()) == {"QUIK", "VICTORY"}
    assert set(ScraperStability.get_always_failing_scrapers()) == set()

    factory_names = set(ScraperFactory.all_listed_scrappers())
    for name in ScraperStability.get_deprecated_scrapers():
        assert name not in factory_names, f"deprecated {name} must not be in factory"

    for name in ScraperStability.get_always_failing_scrapers():
        assert name in factory_names, f"always-failing {name} must stay in factory"
        assert ScraperStability.kind_of(name) is ScraperKind.ALWAYS_FAILING


def test_deprecated_scrapers_match_factory_and_folders():
    """DeprecatedScrapers is the single list used by factory listing and dump folders."""
    deprecated = DeprecatedScrapers.names()
    factory_members = {member.name for member in ScraperFactory}
    folder_members = {member.name for member in DumpFolderNames}

    assert deprecated <= factory_members
    assert deprecated <= folder_members
    assert set(ScraperFactory.get_deprecated_scrapers()) == deprecated
    assert set(ScraperFactory.all_listed_scrappers()) & deprecated == set()
    assert set(DumpFolderNames.active_folder_names()) & deprecated == set()
    assert set(DumpFolderNames.active_folder_names()) == set(
        ScraperFactory.all_listed_scrappers()
    )
    assert set(ScraperFactory.all_listed_scrappers(include_deprecated=True)) == (
        factory_members
    )
    assert factory_members == folder_members


def test_all_active_excludes_deprecated():
    """Production all_scrapers_name() must not return deprecated scrapers."""
    deprecated = DeprecatedScrapers.names()
    assert set(ScraperFactory.all_scrapers_name()) & deprecated == set()
    for name in deprecated:
        assert ScraperFactory.is_deprecated(name)
        assert not ScraperFactory.is_scraper_enabled(ScraperFactory[name])


def test_always_failing_login_details_match_gov_il():
    """Always-failing scrapers must still be listed in the cached gov.il HTML."""
    gov_il_hosts = get_cpfta_retailer_hosts()
    for name in ScraperStability.get_always_failing_scrapers():
        scraper_cls = ScraperFactory[name].value
        with tempfile.TemporaryDirectory() as tmp:
            instance = scraper_cls(file_output=DiskFileOutput(storage_path=tmp))
            login_details = instance.get_login_details()
            host = href_host(login_details.url)
            assert host in gov_il_hosts, (
                f"{name} host {host!r} from {login_details!r} "
                "is not in cpfta_prices_regulations"
            )


def _login_details_for(name):
    scraper_cls = ScraperFactory[name].value
    with tempfile.TemporaryDirectory() as tmp:
        instance = scraper_cls(file_output=DiskFileOutput(storage_path=tmp))
        return instance.get_login_details()


def test_saturday_empty_listings_are_valid_for_netiv_and_mahsani():
    """Saturday publication gaps are known edge cases, not always-failing."""
    saturday = datetime_in_tlv(2026, 9, 5, 22, 0, 0)
    thursday = datetime_in_tlv(2026, 9, 3, 22, 0, 0)

    assert ScraperStability.is_validate_scraper_found_no_files(
        "NETIV_HASED", when_date=saturday
    )
    assert not ScraperStability.is_validate_scraper_found_no_files(
        "NETIV_HASED", when_date=thursday
    )

    assert ScraperStability.is_validate_scraper_found_no_files(
        "MAHSANI_ASHUK_NEW_SOURCE", when_date=saturday
    )
    assert not ScraperStability.is_validate_scraper_found_no_files(
        "MAHSANI_ASHUK_NEW_SOURCE", when_date=thursday
    )
    with patch(
        "il_supermarket_scarper.scraper_stability._is_saturday_in_israel",
        return_value=True,
    ):
        assert ScraperStability.is_validate_scraper_found_no_files(
            "MAHSANI_ASHUK_NEW_SOURCE"
        )
    afternoon = datetime(2026, 9, 17, 15, 0)
    with patch(
        "il_supermarket_scarper.scraper_stability._is_saturday_in_israel",
        return_value=False,
    ), patch(
        "il_supermarket_scarper.scraper_stability._now",
        return_value=afternoon,
    ):
        assert not ScraperStability.is_validate_scraper_found_no_files(
            "MAHSANI_ASHUK_NEW_SOURCE"
        )


def test_city_market_shops_store_empty_before_noon():
    """Store dumps publish around 11:00 IL; empty listings before noon are valid."""
    store = FileTypesFilters.only_store()
    morning = datetime(2026, 9, 8, 10, 59)
    afternoon = datetime(2026, 9, 8, 13, 0)
    with patch("il_supermarket_scarper.scraper_stability._now", return_value=morning):
        assert ScraperStability.is_validate_scraper_found_no_files(
            "CITY_MARKET_SHOPS", files_types=store
        )
    with patch("il_supermarket_scarper.scraper_stability._now", return_value=afternoon):
        assert not ScraperStability.is_validate_scraper_found_no_files(
            "CITY_MARKET_SHOPS", files_types=store
        )
    assert not ScraperStability.is_validate_scraper_found_no_files(
        "CITY_MARKET_SHOPS", files_types=FileTypesFilters.only_price()
    )


def test_wolt_update_files_only_are_approved_empty():
    """Wolt lists only full Price/Promo dumps; single update types may be empty."""
    afternoon = datetime(2026, 11, 8, 13, 0)
    with patch("il_supermarket_scarper.scraper_stability._now", return_value=afternoon):
        for file_type in FileTypesFilters.all_update_files():
            assert ScraperStability.is_validate_scraper_found_no_files(
                "WOLT", files_types=[file_type]
            )
        for files_types in (
            None,
            FileTypesFilters.only_price(),
            FileTypesFilters.only_promo(),
            FileTypesFilters.only_store(),
            [FileTypesFilters.PRICE_FULL_FILE.name],
            [FileTypesFilters.PROMO_FULL_FILE.name],
            FileTypesFilters.all_update_files(),
        ):
            assert not ScraperStability.is_validate_scraper_found_no_files(
                "WOLT", files_types=files_types
            )


def test_laibcatalog_empty_before_noon_without_date_filter():
    """Victory/Het Cohen/Mahsani catalogs are empty overnight until republish."""
    morning = datetime(2026, 9, 17, 0, 30)
    after_republish = datetime(2026, 9, 17, 9, 0)
    thursday = datetime_in_tlv(2026, 9, 3, 22, 0, 0)
    for name in (
        "VICTORY_NEW_SOURCE",
        "HET_COHEN_NEW_SOURCE",
        "MAHSANI_ASHUK_NEW_SOURCE",
    ):
        with patch(
            "il_supermarket_scarper.scraper_stability._now", return_value=morning
        ), patch(
            "il_supermarket_scarper.scraper_stability._is_saturday_in_israel",
            return_value=False,
        ):
            assert ScraperStability.is_validate_scraper_found_no_files(name)
            assert not ScraperStability.is_validate_scraper_found_no_files(
                name, when_date=thursday
            )
        with patch(
            "il_supermarket_scarper.scraper_stability._now",
            return_value=after_republish,
        ), patch(
            "il_supermarket_scarper.scraper_stability._is_saturday_in_israel",
            return_value=False,
        ):
            assert not ScraperStability.is_validate_scraper_found_no_files(name)


def test_yaynot_store_empty_before_noon():
    """Carrefour store 472 files publish in the morning; other listing stays up."""
    morning = datetime(2026, 9, 17, 0, 30)
    after_republish = datetime(2026, 9, 17, 9, 0)
    with patch("il_supermarket_scarper.scraper_stability._now", return_value=morning):
        assert ScraperStability.is_validate_scraper_found_no_files(
            "YAYNO_BITAN_AND_CARREFOUR", store_id=472
        )
        assert not ScraperStability.is_validate_scraper_found_no_files(
            "YAYNO_BITAN_AND_CARREFOUR"
        )
    with patch(
        "il_supermarket_scarper.scraper_stability._now", return_value=after_republish
    ):
        assert not ScraperStability.is_validate_scraper_found_no_files(
            "YAYNO_BITAN_AND_CARREFOUR", store_id=472
        )


class TestNetivListing(unittest.IsolatedAsyncioTestCase):
    """Netiv listing follows the UI Date filter."""

    async def test_netiv_lists_recent_date_pages(self):
        """The site Date filter defaults to today; also open the prior UI days."""
        with tempfile.TemporaryDirectory() as tmp:
            scraper = NetivHased(file_output=DiskFileOutput(storage_path=tmp))
            urls = []
            async for request in scraper.get_request_url():
                urls.append(request["url"])

        self.assertEqual(len(urls), 3)
        self.assertTrue(all("Date=" in url for url in urls))

        saturday = date(2026, 9, 5)
        with tempfile.TemporaryDirectory() as tmp:
            scraper = NetivHased(file_output=DiskFileOutput(storage_path=tmp))
            urls = []
            async for request in scraper.get_request_url(when_date=saturday):
                urls.append(request["url"])
        self.assertEqual(urls, ["https://app.netiv-hesed.com/?Date=2026-09-05"])


def test_login_details_include_credentials_when_set():
    """Username and password are included only when the scraper has them."""
    web = _login_details_for("NETIV_HASED")
    assert web.url == "https://app.netiv-hesed.com/"
    assert web.username is None
    assert web.password is None

    ftp_user_only = _login_details_for("RAMI_LEVY")
    assert ftp_user_only.url == "ftp://url.retail.publishedprices.co.il/"
    assert ftp_user_only.username == "RamiLevi"
    assert ftp_user_only.password is None

    ftp_with_password = _login_details_for("YELLOW")
    assert ftp_with_password.url == "ftp://url.retail.publishedprices.co.il/"
    assert ftp_with_password.username == "Paz_bo"
    assert ftp_with_password.password == "paz468"


def test_meshnat_yosef_promo_empty_for_any_promo_only_request():
    """MESHMAT_YOSEF_1 doesn't publish promos: any promo-only request may be empty."""
    promo = FileTypesFilters.PROMO_FILE.name
    promo_full = FileTypesFilters.PROMO_FULL_FILE.name
    for files_types in (
        [promo],
        [promo_full],
        [promo, promo_full],
        [promo_full, promo],
        (promo_full,),
    ):
        assert ScraperStability.is_validate_scraper_found_no_files(
            "MESHMAT_YOSEF_1", files_types=files_types
        ), files_types


def test_meshnat_yosef_promo_rule_does_not_cover_other_types():
    """A request that includes prices or stores, or no filter, must not pass empty."""
    afternoon = datetime(2026, 9, 17, 15, 0)
    promo = FileTypesFilters.PROMO_FILE.name
    with patch(
        "il_supermarket_scarper.scraper_stability._now", return_value=afternoon
    ), patch.object(
        MeshnatYosef1WorkerOutage, "listing_worker_failing", return_value=False
    ):
        for files_types in (
            None,
            [],
            FileTypesFilters.only_price(),
            FileTypesFilters.only_store(),
            [promo, FileTypesFilters.PRICE_FILE.name],
            FileTypesFilters.all_types(),
        ):
            assert not ScraperStability.is_validate_scraper_found_no_files(
                "MESHMAT_YOSEF_1", files_types=files_types
            ), files_types


def _probe_response(status_code, text):
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    return response


def test_meshnat_yosef_worker_outage_approves_empty_only_while_failing():
    """#229: empty is approved while the listing worker throws, not otherwise."""
    afternoon = datetime(2026, 11, 10, 15, 0)
    probe = "il_supermarket_scarper.scraper_stability.requests.get"
    price = FileTypesFilters.only_price()
    with patch("il_supermarket_scarper.scraper_stability._now", return_value=afternoon):
        for failing in (
            _probe_response(500, "<title>Worker threw exception</title>"),
            _probe_response(200, "error code: 1101"),
            _probe_response(503, ""),
        ):
            with patch(probe, return_value=failing):
                assert ScraperStability.is_validate_scraper_found_no_files(
                    "MESHMAT_YOSEF_1", files_types=price
                )
        for healthy in (
            _probe_response(200, '[{"type":"PriceFull","name":"x"}]'),
            _probe_response(200, "[]"),
            _probe_response(404, "not found"),
        ):
            with patch(probe, return_value=healthy):
                assert not ScraperStability.is_validate_scraper_found_no_files(
                    "MESHMAT_YOSEF_1", files_types=price
                )
        with patch(probe, side_effect=requests.ConnectionError("refused")):
            assert not ScraperStability.is_validate_scraper_found_no_files(
                "MESHMAT_YOSEF_1", files_types=price
            )


def test_meshnat_yosef_worker_outage_expires():
    """After the outage expiration date a failing worker is a test failure again."""
    afternoon = datetime(2026, 11, 10, 15, 0)
    with patch(
        "il_supermarket_scarper.scraper_stability._now", return_value=afternoon
    ), patch.object(
        MeshnatYosef1WorkerOutage, "listing_worker_failing", return_value=True
    ), patch.object(
        MeshnatYosef1WorkerOutage,
        "outage_expiration_date",
        return_value=datetime(2000, 1, 1),
    ):
        assert not ScraperStability.is_validate_scraper_found_no_files(
            "MESHMAT_YOSEF_1", files_types=FileTypesFilters.only_price()
        )


def test_meshnat_yosef_worker_outage_rule_is_scoped_to_meshnat_yosef_1():
    """The probe is only consulted for MESHMAT_YOSEF_1."""
    assert ScraperStability["MESHMAT_YOSEF_1"].value is MeshnatYosef1WorkerOutage
    assert issubclass(MeshnatYosef1WorkerOutage, DoNotPublishPromo)
    for name, member in ScraperStability.__members__.items():
        if name != "MESHMAT_YOSEF_1":
            assert not issubclass(member.value, MeshnatYosef1WorkerOutage), name


def test_store_only_rules_match_by_content_not_list_identity():
    """Store-only rules accept any store-only sequence and reject mixed requests."""
    afternoon = datetime(2026, 9, 17, 15, 0)
    store = FileTypesFilters.STORE_FILE.name
    with patch("il_supermarket_scarper.scraper_stability._now", return_value=afternoon):
        for name in ("SUPER_YUDA", "YELLOW"):
            assert ScraperStability.is_validate_scraper_found_no_files(
                name, files_types=(store,)
            )
            assert not ScraperStability.is_validate_scraper_found_no_files(
                name, files_types=[store, FileTypesFilters.PRICE_FILE.name]
            )
            assert not ScraperStability.is_validate_scraper_found_no_files(
                name, files_types=None
            )


def test_yellow_promo_update_empty_only_on_weekend():
    """Yellow Promo (update) files are sparse on Saturday and late on Sunday.

    Only an exact ``[PROMO_FILE]`` request is approved, only on Saturday or on
    Sunday before 18:00 IL. Weekdays and every other file type stay strict.
    """
    promo = [FileTypesFilters.PROMO_FILE.name]
    saturday = datetime_in_tlv(2026, 11, 7, 15, 0, 0)
    sunday_afternoon = datetime_in_tlv(2026, 11, 8, 15, 35, 0)
    sunday_evening = datetime_in_tlv(2026, 11, 8, 19, 0, 0)
    monday_noon = datetime_in_tlv(2026, 11, 9, 12, 30, 0)
    thursday = datetime_in_tlv(2026, 11, 5, 14, 0, 0)

    def approved(now, when_date, files_types=tuple(promo), name="YELLOW"):
        with patch("il_supermarket_scarper.scraper_stability._now", return_value=now):
            return ScraperStability.is_validate_scraper_found_no_files(
                name, files_types=files_types, when_date=when_date, limit=10
            )

    # Saturday, any hour, and a Saturday asked for later.
    assert approved(saturday, saturday)
    assert approved(monday_noon, saturday)
    # Sunday today, before 18:00 IL (the 2026-11-08 CI failure).
    assert approved(sunday_afternoon, sunday_afternoon)
    assert approved(sunday_afternoon, None)
    # Sunday after 18:00, or a past Sunday, must have files.
    assert not approved(sunday_evening, sunday_evening)
    assert not approved(monday_noon, sunday_afternoon)
    # Weekdays stay strict.
    assert not approved(monday_noon, monday_noon)
    assert not approved(thursday, thursday)
    # Other file types and other chains stay strict on the weekend too.
    for files_types in (
        FileTypesFilters.only_promo(),
        [FileTypesFilters.PROMO_FULL_FILE.name],
        [FileTypesFilters.PRICE_FILE.name],
        [FileTypesFilters.PRICE_FULL_FILE.name],
        None,
    ):
        assert not approved(saturday, saturday, files_types=files_types)
        assert not approved(sunday_afternoon, sunday_afternoon, files_types=files_types)
    assert not approved(saturday, saturday, name="YOHANANOF")
