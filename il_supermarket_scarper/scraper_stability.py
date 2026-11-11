# pylint: disable=arguments-differ,arguments-renamed
import json
import warnings
from datetime import datetime
from enum import Enum

import requests

from il_supermarket_scarper.utils import (
    _now,
    _testing_now,
    _is_saturday_in_israel,
    datetime_in_tlv,
    FileTypesFilters,
    hour_files_expected_to_be_accassible,
)
from il_supermarket_scarper.utils.core.logger import Logger


def requests_only(files_types, allowed):
    """True if ``files_types`` is a non-empty request made only of ``allowed`` types.

    Order and container type don't matter, so ``[PROMO_FULL_FILE]``,
    ``[PROMO_FILE, PROMO_FULL_FILE]`` and its reverse all match the promo
    types. ``None`` (no filter, i.e. every type) and ``[]`` never match.
    """
    if not files_types:
        return False
    return set(files_types) <= {file_type.name for file_type in allowed}


class ScraperKind(Enum):
    """How a scraper is expected to behave in tests and production."""

    # Listed on gov.il; failire_valid() covers known edge cases only
    EDGE_CASE = "edge_case"
    # Listed on gov.il; every scrape is expected to fail
    ALWAYS_FAILING = "always_failing"
    # Gone from gov.il; keep the class for historical folder mapping, do not run
    DEPRECATED = "deprecated"


class FullyStable:
    """fully stable is stablity"""

    kind = ScraperKind.EDGE_CASE

    @classmethod
    def pass_expiration_date(cls):
        """return the expiration date"""
        return datetime(2027, 1, 1)

    @classmethod
    def executes_between_midnight_and_morning_and_requested_today(
        cls,
        when_date=None,
        utilize_date_param=False,
    ):
        """it is stable if the execution is between midnight
        and morning and the requested date is the test probe date"""
        del utilize_date_param  # kept for call-site compatibility
        execution_time = _now()
        # Before the usual morning publish window, scraper tests probe with
        # `_testing_now()` (rolled back from calendar today). Suppress missing
        # files only for that probe date—not arbitrary historical when_date.
        return (
            when_date is not None
            and 0 <= execution_time.hour < hour_files_expected_to_be_accassible()
            and when_date.date() == _testing_now().date()
        )

    @classmethod
    def executed_after_date(cls, when_date, date):
        """check if executed after date"""
        return when_date > date

    @classmethod
    def failire_valid(cls, *, when_date=None, utilize_date_param=True, **_):
        """return true if the parser is stble"""

        return cls.executes_between_midnight_and_morning_and_requested_today(
            when_date=when_date, utilize_date_param=utilize_date_param
        )


class AlwaysFailing(FullyStable):
    """Still listed on gov.il; every scrape is expected to fail."""

    kind = ScraperKind.ALWAYS_FAILING

    @classmethod
    def failire_valid(cls, **_):
        return True


class DeprecatedScraper(FullyStable):
    """Removed from gov.il; keep the class for historical folder mapping."""

    kind = ScraperKind.DEPRECATED

    @classmethod
    def pass_expiration_date(cls):
        return datetime(9999, 5, 1)

    @classmethod
    def failire_valid(cls, **_):
        return True


class SuperFlaky(FullyStable):
    """super flaky is stablity"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 1, 1)

    @classmethod
    def failire_valid(cls, **_):
        return True


class NetivHased(FullyStable):
    """app.netiv-hesed.com Date filter lists 0 files on Saturday.

    Evidence 2026-09-05: UI shows 0 files for 2026-09-05, last update
    2026-09-04 16:20, and 367 files for 2026-09-04. Cloudflare blocks
    requests without a browser User-Agent. Still listed on CPFTA.
    """

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        return super(cls, NetivHased).failire_valid(
            when_date=when_date,
            files_types=files_types,
            utilize_date_param=utilize_date_param,
        ) or (when_date is not None and _is_saturday_in_israel(when_date))


class LaibcatalogOvernightEmpty(FullyStable):
    """laibcatalog getfiles returns [] between midnight and morning republish.

    Nightly CI is often queued past midnight IL. Tests without when_date then
    see an empty catalog even though getbranches still lists stores. The SPA
    lists files again after the morning drop (around 08:00 IL). Cut off at
    08:00 so production still scrapes the rest of the morning.
    """

    empty_until_hour = 8

    @classmethod
    def overnight_empty_catalog(cls, when_date=None):
        """Empty catalog before the morning republish, when no date filter."""
        return when_date is None and _now().hour < cls.empty_until_hour

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        return super().failire_valid(
            when_date=when_date,
            files_types=files_types,
            utilize_date_param=utilize_date_param,
        ) or cls.overnight_empty_catalog(when_date=when_date)


class MahsaniAshukNewSource(LaibcatalogOvernightEmpty):
    """laibcatalog mshuk getfiles returns [] on Saturday and overnight.

    Evidence 2026-09-04: evening CI collected Mahsani files (not in the
    failed list). Evidence 2026-09-05: getfiles?edi=7290661400001 returns
    []; mshuk UI uses that DEFAULT_EDI and shows no files. Evidence
    2026-09-14..17: scheduled CI after midnight IL retrieved 0 files
    while getbranches still listed 71 stores. Evidence 2026-09-18
    morning: mshuk SPA listed 428 files dated 08:11
    (https://laibcatalog.co.il/mshuk/index.html). CPFTA still lists
    מחסני השוק (mshuk).
    """

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        saturday_gap = (
            _is_saturday_in_israel(when_date)
            if when_date is not None
            else _is_saturday_in_israel()
        )
        return super().failire_valid(
            when_date=when_date,
            files_types=files_types,
            utilize_date_param=utilize_date_param,
        ) or saturday_gap


class VictoryNewSource(LaibcatalogOvernightEmpty):
    """laibcatalog victory getfiles returns [] after midnight until republish.

    Evidence 2026-09-14..17: scheduled CI after midnight IL retrieved 0
    files (getfiles JSON []) while getbranches still listed stores.
    Evidence 2026-09-18 morning: victory SPA listed 690 files dated
    09:07 (https://laibcatalog.co.il/victory/index.html). CPFTA still
    lists ויקטורי.
    """


class HetCohenNewSource(LaibcatalogOvernightEmpty):
    """laibcatalog hcohen getfiles returns [] after midnight until republish.

    Evidence 2026-09-14..17: scheduled CI after midnight IL retrieved 0
    files while getbranches still listed 5 stores. Evidence 2026-09-18
    morning: hcohen SPA listed 41 files dated 08:02 including store 1
    (https://laibcatalog.co.il/hcohen/index.html). CPFTA still lists ח. כהן.
    """


class CityMarketGivataim(FullyStable):
    """Netiv Hased is stablity"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 1, 1)

    @classmethod
    def searching_for_update_promo(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return requests_only(files_types, [FileTypesFilters.PROMO_FILE])

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return (
            super(cls, CityMarketGivataim).failire_valid(when_date=when_date)
            or cls.searching_for_update_promo(files_types=files_types)
            or when_date is not None
            and cls.executed_after_date(
                when_date=when_date,
                date=datetime_in_tlv(
                    year=2024, month=11, day=5, hour=0, minute=0, second=0
                ),
            )
        )


class CityMarketKiratOno(FullyStable):
    """Netiv Hased is stablity"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 1, 1)

    @classmethod
    def searching_for_update_promo(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return requests_only(files_types, [FileTypesFilters.PROMO_FILE])

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return super(cls, CityMarketKiratOno).failire_valid(
            when_date=when_date
        ) or cls.searching_for_update_promo(files_types=files_types)


class CityMarketKiratGat(AlwaysFailing):
    """Still on gov.il; expected to fail until the scraper is reliable."""


class DoNotPublishStores(FullyStable):
    """stablity for chains that doesn't pubish stores"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(9999, 5, 1)  # quik is only, they don't publish stores

    @classmethod
    def searching_for_store_full(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return requests_only(files_types, [FileTypesFilters.STORE_FILE])

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return super(cls, DoNotPublishStores).failire_valid(
            when_date=when_date,
            files_types=files_types,
            utilize_date_param=utilize_date_param,
        ) or cls.searching_for_store_full(files_types=files_types)


class YaynotBitanAndCarrefour(FullyStable):
    """Carrefour per-store files for some branches publish after midnight.

    Evidence 2026-09-14..17: test_scrape_one found files after midnight IL
    but store_id=472 listed 0. Evidence 2026-09-18: prices.carrefour.co.il
    lists store 472 (יהלומים ביתן) with files from 05:10-07:00.
    """

    empty_until_hour = 8

    @classmethod
    def searching_for_store_before_noon(cls, store_id=None, **_):
        """Some store dumps are missing until the morning publish window."""
        return store_id is not None and _now().hour < cls.empty_until_hour

    @classmethod
    def failire_valid(
        cls,
        when_date=None,
        files_types=None,
        utilize_date_param=True,
        store_id=None,
        **_,
    ):
        return super().failire_valid(
            when_date=when_date,
            files_types=files_types,
            utilize_date_param=utilize_date_param,
        ) or cls.searching_for_store_before_noon(store_id=store_id)


class CityMarketShopsStores(FullyStable):
    """City Market Shops store dumps publish around 11:00 IL.

    Evidence 2026-09-08: CI at 10:59 IL listed 0 store files; the day's
    ``StoresFull7290000000003`` dump is timestamped 11:00. Price/promo
    scrapes on the same run succeeded. After noon IL the store file is listed.
    """

    @classmethod
    def searching_for_store_before_noon(cls, files_types=None, **_):
        """Store-only scrapes before the usual publish window may be empty."""
        if not requests_only(files_types, [FileTypesFilters.STORE_FILE]):
            return False
        return _now().hour < hour_files_expected_to_be_accassible()

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return super(cls, CityMarketShopsStores).failire_valid(
            when_date=when_date,
            files_types=files_types,
            utilize_date_param=utilize_date_param,
        ) or cls.searching_for_store_before_noon(files_types=files_types)


class SuperYuda(FullyStable):
    """Super Yuda is stablity"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 1, 1)

    @classmethod
    def searching_for_store_full(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return requests_only(files_types, [FileTypesFilters.STORE_FILE])

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return super(cls, SuperYuda).failire_valid(
            when_date=when_date,
            files_types=files_types,
            utilize_date_param=utilize_date_param,
        ) or cls.searching_for_store_full(files_types=files_types)


class Yellow(FullyStable):
    """Yellow (Paz / יילו) does not publish store files.

    Evidence 2026-08-30: FTP url.retail.publishedprices.co.il user Paz_bo
    listed 591 Price/Promo files (dated 2026-08-30) and 0 filenames containing
    'store'. Root listing has no subdirectories. Other Yellow file types scrape
    successfully. CPFTA still lists יילו (page update 12.08.2026):
    https://www.gov.il/he/pages/cpfta_prices_regulations

    Yellow publishes few or no Promo (update) files over the weekend (issue
    #220). Evidence from the daily Kaggle scraper status (versions 600-718,
    2026-08-07..11-08, 86 days, every file Yellow listed for the scraped
    day):

    - Saturday: 0 Promo files on 6 of 13 Saturdays (08-08, 08-15, 08-22,
      09-19, 10-31, 11-07); most others had 2-20.
    - Sunday: the first Promo file came at 11:00 IL or later on 8 of 13
      Sundays (latest 17:00 on 10-25; 16:00 on 11-08, when parsers CI at
      15:35 IL listed 0 with no FTP error), and 09-20 had none.
    - Monday-Thursday: the first Promo file came between 06:00 and 10:00 IL
      on 44 of 46 days. Weekday gaps (e.g. 11-05, 11-06) are sporadic, so
      weekdays stay strict.

    So an empty ``[PROMO_FILE]`` request is approved only for a Saturday, or
    for today when today is Sunday and it is before 18:00 IL.
    """

    sunday_promo_until_hour = 18

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 1, 1)

    @classmethod
    def searching_for_store_full(cls, files_types=None, **_):
        """Yellow FTP listing contains no store files."""
        return requests_only(files_types, [FileTypesFilters.STORE_FILE])

    @classmethod
    def weekend_promo_gap(cls, when_date=None, files_types=None, **_):
        """Promo (update) files are sparse on Saturday and late on Sunday."""
        if files_types is None or list(files_types) != [
            FileTypesFilters.PROMO_FILE.name
        ]:
            return False
        now = _now()
        day = when_date if when_date is not None else now
        if _is_saturday_in_israel(day):
            return True
        return (
            day.weekday() == 6
            and day.date() == now.date()
            and now.hour < cls.sunday_promo_until_hour
        )

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return (
            super(cls, Yellow).failire_valid(
                when_date=when_date,
                files_types=files_types,
                utilize_date_param=utilize_date_param,
            )
            or cls.searching_for_store_full(files_types=files_types)
            or cls.weekend_promo_gap(when_date=when_date, files_types=files_types)
        )


class QuikSiteIsDown(DeprecatedScraper):
    """Quik no longer has a dedicated gov.il listing (folded into Carrefour)."""


class PublishOnlyStores(FullyStable):
    """Publish only stores"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 5, 1)

    @classmethod
    def searching_for_not_store_full(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return (
            files_types is not None
            and FileTypesFilters.STORE_FILE.name not in files_types
        )

    @classmethod
    def search_for_a_specific_store(cls, store_id=None, **_):
        """if the store id is match"""
        return store_id is not None

    @classmethod
    def failire_valid(
        cls,
        when_date=None,
        files_types=None,
        utilize_date_param=True,
        store_id=None,
        **_,
    ):
        return (
            super(cls, PublishOnlyStores).failire_valid(
                when_date=when_date,
                files_types=files_types,
                utilize_date_param=utilize_date_param,
            )
            or cls.searching_for_not_store_full(
                files_types=files_types, store_id=store_id
            )
            or cls.search_for_a_specific_store(store_id=store_id)
        )


class DoNotPublishPromo(FullyStable):
    """stablity for chains that don't publish promo files"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 1, 1)  # will give it one more year

    @classmethod
    def searching_for_promo_full(cls, files_types=None, **_):
        """the request asks only for promo types (one or both, any order)"""
        return requests_only(
            files_types,
            [FileTypesFilters.PROMO_FILE, FileTypesFilters.PROMO_FULL_FILE],
        )

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return super(cls, DoNotPublishPromo).failire_valid(
            when_date=when_date,
            files_types=files_types,
            utilize_date_param=utilize_date_param,
        ) or cls.searching_for_promo_full(files_types=files_types)


class MeshnatYosef1WorkerOutage(DoNotPublishPromo):
    """Meshnat Yosef 1's Cloudflare Worker listing sometimes throws (issue #229).

    The scraper lists files from https://list-files.w5871031-kt.workers.dev/.
    Evidence 2026-11-09 20:24 and 21:38 UTC: CI run 42685615848 got HTTP 500
    on every attempt and all 5 listing tests failed; a direct curl at 21:40
    UTC got ``error code: 1101`` (Cloudflare "Worker threw exception").
    Evidence 2026-11-10 20:46 UTC: main run 42894721038 got the Cloudflare
    1101 page on all 4 retries for ``test_scrape_file_today`` while the other
    Meshnat Yosef 1 tests in that run passed. Evidence 2026-11-11 06:30 UTC:
    15 of 15 requests returned 200 with that day's PriceFull and Stores files,
    and all 7 MeshnatYosef1TestCase tests passed. The source is live, its
    worker fails intermittently on their side.

    Empty results are approved only while the worker is failing right now:
    the rule probes the listing URL and approves when it answers 5xx or with
    a Cloudflare worker-exception body. A healthy listing that returns no
    files, or any other failure, is not covered. Expires on its own date,
    separate from the promo rule.
    """

    listing_url = "https://list-files.w5871031-kt.workers.dev/"
    worker_error_markers = ("error code: 1101", "Worker threw exception")
    probe_timeout_seconds = 20

    @classmethod
    def outage_expiration_date(cls):
        """the worker-outage approval expires before the promo rule"""
        return datetime(2026, 12, 31)

    @classmethod
    def listing_worker_failing(cls):
        """True if the listing worker answers 5xx or a worker-exception body."""
        try:
            response = requests.get(cls.listing_url, timeout=cls.probe_timeout_seconds)
        except requests.RequestException as error:
            Logger.warning(f"Meshnat Yosef 1 listing probe failed to connect: {error}")
            return False
        body = response.text or ""
        failing = response.status_code >= 500 or any(
            marker in body for marker in cls.worker_error_markers
        )
        if failing:
            Logger.warning(
                f"Meshnat Yosef 1 listing worker is failing: "
                f"status {response.status_code}, body {body[:80]!r}"
            )
        return failing

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        # DoNotPublishPromo calls super() with its own name as the instance,
        # so call it directly rather than through super(cls, ...).
        if DoNotPublishPromo.failire_valid(
            when_date=when_date,
            files_types=files_types,
            utilize_date_param=utilize_date_param,
        ):
            return True
        return (
            cls.outage_expiration_date() > datetime.now()
            and cls.listing_worker_failing()
        )


class WoltPublishesOnlyFullFiles(FullyStable):
    """Wolt publishes full Price/Promo dumps only, no update files.

    Evidence 2026-11-08: the index at
    https://wm-gateway.wolt.com/isr-prices/public/v1/index.html lists 93 days
    (2026-08-08 to 2026-11-08). Across them: 3186 PriceFull, 3186 PromoFull,
    93 Stores and 0 Promo (non-full) files. Price (non-full) files appear only
    on 2026-09-26 (88), 2026-09-27 (160) and 2026-09-28 (96). A single-type
    scrape of [PRICE_FILE] for 2026-09-27 returns them, so the filter works.
    Parsers nightly skipped WoltTestCase::test_parsing_prices/promo for "no
    files downloaded" in 25 of 25 runs (2026-10-10 to 2026-11-03).
    Approve an empty result only for a request of a single update type.
    """

    @classmethod
    def searching_for_update_file_only(cls, files_types=None, **_):
        """A request for only PRICE_FILE or only PROMO_FILE."""
        return files_types in (
            [FileTypesFilters.PRICE_FILE.name],
            [FileTypesFilters.PROMO_FILE.name],
        )

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return super().failire_valid(
            when_date=when_date,
            files_types=files_types,
            utilize_date_param=utilize_date_param,
        ) or cls.searching_for_update_file_only(files_types=files_types)


class VictoryMovedToNewSource(DeprecatedScraper):
    """Old Victory source; gov.il lists VICTORY_NEW_SOURCE only."""


STALE_STABILITY_RULE_MARKER = "STALE_STABILITY_RULE"


class StaleStabilityRuleWarning(RuntimeWarning):
    """A stability rule approved "no files" but the scraper returned files.

    Not a ``UserWarning`` subclass on purpose: pytest.ini ignores those, and
    this one must reach pytest's warnings summary so the weekly
    stale-stability-rules workflow can grep it.
    """


class ScraperStability(Enum):
    """tracker for the stablity of the scraper"""

    # COFIX = DoNotPublishStores
    NETIV_HASED = NetivHased
    MAHSANI_ASHUK_NEW_SOURCE = MahsaniAshukNewSource
    VICTORY_NEW_SOURCE = VictoryNewSource
    HET_COHEN_NEW_SOURCE = HetCohenNewSource
    YAYNO_BITAN_AND_CARREFOUR = YaynotBitanAndCarrefour
    QUIK = QuikSiteIsDown
    SUPER_YUDA = SuperYuda
    YELLOW = Yellow
    COFIX = PublishOnlyStores
    # SALACH_DABACH = DoNotPublishStores
    # # CITY_MARKET_GIVATAYIM = CityMarketGivataim
    # CITY_MARKET_KIRYATONO = CityMarketKiratOno
    # CITY_MARKET_KIRYATGAT = CityMarketKiratGat  # recovered 2026-08-30: bina portal lists files
    CITY_MARKET_SHOPS = CityMarketShopsStores
    MESHMAT_YOSEF_1 = MeshnatYosef1WorkerOutage
    VICTORY = VictoryMovedToNewSource
    WOLT = WoltPublishesOnlyFullFiles
    # YOHANANOF = DoNotPublishStores

    @classmethod
    def is_validate_scraper_found_no_files(
        cls,
        scraper_enum,
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        utilize_date_param=False,
    ):
        """return true if its ok the scarper reuturn no enrty"""

        stabler = FullyStable
        if scraper_enum in ScraperStability.__members__:
            stabler = ScraperStability[scraper_enum].value

        expected_to_fail = (
            stabler.failire_valid(
                limit=limit,
                files_types=files_types,
                store_id=store_id,
                when_date=when_date,
                utilize_date_param=utilize_date_param,
            )
            and stabler.pass_expiration_date() > datetime.now()
        )

        if expected_to_fail:
            Logger.warning(
                f"scraper {scraper_enum} is not stable, "
                f"pass_expiration_date: {stabler.pass_expiration_date().strftime('%Y-%m-%d')}, "
                f"datetime.now(): {datetime.now().strftime('%Y-%m-%d')}"
            )
        return expected_to_fail

    @classmethod
    def warn_if_files_found_when_empty_approved(  # pylint: disable=too-many-arguments
        cls,
        scraper_enum,
        files_found,
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        utilize_date_param=False,
    ):
        """Warn when a chain-specific rule approved "no files" but files came back.

        The rule may be stale (the chain started publishing again). Only
        scrapers registered here are checked; always-failing scrapers already
        fail their test and deprecated ones are not run. Approval that comes
        only from the generic ``FullyStable`` probe window is not reported.
        Returns True if it warned.
        """
        if not files_found or scraper_enum not in cls.__members__:
            return False
        if cls.kind_of(scraper_enum) is not ScraperKind.EDGE_CASE:
            return False
        stabler = cls[scraper_enum].value
        if stabler.pass_expiration_date() <= datetime.now():
            return False
        params = {
            "limit": limit,
            "files_types": files_types,
            "store_id": store_id,
            "when_date": when_date,
            "utilize_date_param": utilize_date_param,
        }
        if not stabler.failire_valid(**params) or FullyStable.failire_valid(**params):
            return False

        payload = {
            "scraper": scraper_enum,
            "rule": stabler.__name__,
            "files_found": int(files_found),
            "files_types": list(files_types) if files_types else None,
            "store_id": store_id,
            "when_date": when_date.isoformat() if when_date is not None else None,
            "limit": limit,
        }
        message = f"{STALE_STABILITY_RULE_MARKER} {json.dumps(payload, sort_keys=True)}"
        Logger.warning(message)
        warnings.warn(message, StaleStabilityRuleWarning, stacklevel=2)
        return True

    @classmethod
    def kind_of(cls, name):
        """Return the ScraperKind for a scraper name, defaulting to EDGE_CASE."""
        if name not in cls.__members__:
            return ScraperKind.EDGE_CASE
        return getattr(cls[name].value, "kind", ScraperKind.EDGE_CASE)

    @classmethod
    def names_of_kind(cls, kind):
        """Return scraper names registered with the given ScraperKind."""
        return [name for name in cls.__members__ if cls.kind_of(name) is kind]

    @classmethod
    def is_deprecated(cls, name):
        """True if this scraper was removed from gov.il and should not be run."""
        return cls.kind_of(name) is ScraperKind.DEPRECATED

    @classmethod
    def is_always_failing(cls, name):
        """True if every scrape is expected to fail, but the retailer is on gov.il."""
        return cls.kind_of(name) is ScraperKind.ALWAYS_FAILING

    @classmethod
    def get_always_failing_scrapers(cls):
        """Scrapers that still must be listed on gov.il and are expected to fail."""
        return cls.names_of_kind(ScraperKind.ALWAYS_FAILING)

    @classmethod
    def get_deprecated_scrapers(cls):
        """Scrapers removed from gov.il; kept only for historical mapping."""
        return cls.names_of_kind(ScraperKind.DEPRECATED)
