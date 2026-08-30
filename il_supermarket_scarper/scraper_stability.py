# pylint: disable=arguments-differ,arguments-renamed
import tempfile
from datetime import datetime
from enum import Enum

import il_supermarket_scarper.scrappers as all_scrappers
from il_supermarket_scarper.utils import (
    _now,
    _testing_now,
    datetime_in_tlv,
    DumpFolderNames,
    FileTypesFilters,
    hour_files_expected_to_be_accassible,
)
from il_supermarket_scarper.utils.file_output import DiskFileOutput
from il_supermarket_scarper.utils.logger import Logger


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
            and execution_time.hour >= 0
            and execution_time.hour < hour_files_expected_to_be_accassible()
            and when_date.date() == _testing_now().date()
        )

    @classmethod
    def executed_after_date(cls, when_date, date):
        """check if executed after date"""
        return when_date > date

    @classmethod
    def failire_valid(cls, when_date=None, utilize_date_param=True, **_):
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


class NetivHased(AlwaysFailing):
    """Still on gov.il; scraper URL must match the cached listing."""


class CityMarketGivataim(FullyStable):
    """Netiv Hased is stablity"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 1, 1)

    @classmethod
    def searching_for_update_promo(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return files_types and files_types == [FileTypesFilters.PROMO_FILE.name]

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
        return files_types and files_types == [FileTypesFilters.PROMO_FILE.name]

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
        return files_types and files_types == [FileTypesFilters.STORE_FILE.name]

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


class SuperYuda(FullyStable):
    """Super Yuda is stablity"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 1, 1)

    @classmethod
    def searching_for_store_full(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return files_types and files_types == [FileTypesFilters.STORE_FILE.name]

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
    """stablity for chains that doesn't pubish stores"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 1, 1)  # will give it one more year

    @classmethod
    def searching_for_promo_full(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return files_types and files_types == [
            FileTypesFilters.PROMO_FILE.name,
            FileTypesFilters.PROMO_FULL_FILE.name,
        ]

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


class VictoryMovedToNewSource(DeprecatedScraper):
    """Old Victory source; gov.il lists VICTORY_NEW_SOURCE only."""


class ScraperStability(Enum):
    """tracker for the stablity of the scraper"""

    # COFIX = DoNotPublishStores
    NETIV_HASED = NetivHased
    QUIK = QuikSiteIsDown
    SUPER_YUDA = SuperYuda
    COFIX = PublishOnlyStores
    # SALACH_DABACH = DoNotPublishStores
    # # CITY_MARKET_GIVATAYIM = CityMarketGivataim
    # CITY_MARKET_KIRYATONO = CityMarketKiratOno
    CITY_MARKET_KIRYATGAT = CityMarketKiratGat
    MESHMAT_YOSEF_1 = DoNotPublishPromo
    VICTORY = VictoryMovedToNewSource
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
