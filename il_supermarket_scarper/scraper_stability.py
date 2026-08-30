# pylint: disable=arguments-differ,arguments-renamed
from enum import Enum
from datetime import datetime

from il_supermarket_scarper.utils import (
    _now,
    _testing_now,
    datetime_in_tlv,
    FileTypesFilters,
    hour_files_expected_to_be_accassible,
)
from il_supermarket_scarper.utils.logger import Logger


class FullyStable:
    """fully stable is stablity"""

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


class SuperFlaky(FullyStable):
    """super flaky is stablity"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 1, 1)

    @classmethod
    def failire_valid(cls, **_):
        return True


class NetivHased(FullyStable):
    """Netiv Hased site is down (HTTP 500 on http://141.226.203.152/).

    Evidence: upstream returns HTTP 500 for store/price/promo scrapes as of
    2026-07-24 (CI NetivHasefTestCase all failing). Previously Saturday-only;
    site is now unavailable on weekdays too.
    """

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 1, 1)

    @classmethod
    def failire_valid(cls, **_):
        """return true if missing files are expected"""
        return True


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


class CityMarketKiratGat(FullyStable):
    """Netiv Hased is stablity"""

    @classmethod
    def pass_expiration_date(cls):
        """return the expiration date"""
        return datetime(2027, 3, 1)

    @classmethod
    def searching_for_update_promo_full(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return files_types and files_types == [FileTypesFilters.PROMO_FULL_FILE.name]

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return (
            super(cls, CityMarketKiratGat).failire_valid(
                when_date=when_date,
                files_types=files_types,
                utilize_date_param=utilize_date_param,
            )
            or True
        )  # there is an active issue with the site


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


class QuikSiteIsDown(FullyStable):
    """Quik site is down"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(2027, 5, 1)

    @classmethod
    def failire_valid(cls, **_):
        return True


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


class VictoryMovedToNewSource(FullyStable):
    """Victory moved to new source"""

    @classmethod
    def pass_expiration_date(cls):
        return datetime(9999, 5, 1)

    @classmethod
    def failire_valid(cls, **_):
        return True


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
    def get_permanently_failing_scrapers(cls):
        """Return scraper names with unconditional failire_valid() methods.

        These are scrapers whose failire_valid() always returns True regardless
        of parameters, indicating a permanent site outage. If such a scraper
        starts returning files, it may have recovered and should be re-evaluated.
        """
        unconditional = []
        for name in cls.__members__:
            stabler = cls[name].value
            if stabler.pass_expiration_date() <= datetime.now():
                continue
            test_result = stabler.failire_valid(
                when_date=None,
                files_types=None,
                store_id=None,
                utilize_date_param=False,
            )
            if test_result:
                unconditional.append(name)
        return unconditional
