# pylint: disable=arguments-differ,arguments-renamed
from enum import Enum
from il_supermarket_scarper.utils import (
    _is_saturday_in_israel,
    _now,
    datetime_in_tlv,
    FileTypesFilters,
    hour_files_expected_to_be_accassible,
)


class FullyStable:
    """fully stable is stablity"""

    @classmethod
    def executes_between_midnight_and_morning_and_requested_today(
        cls,
        when_date=None,
        utilize_date_param=False,
    ):
        """it is stable if the execution is between midnight
        and morning and the requested date is today fails"""
        execution_time = _now()
        return (
            when_date is not None
            and execution_time.hour >= 0
            and execution_time.hour < hour_files_expected_to_be_accassible()
            and (not utilize_date_param or when_date.date() == execution_time.date())
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
    def failire_valid(cls, **_):
        return True


class NetivHased(FullyStable):
    """Netiv Hased is stablity"""

    @classmethod
    def executed_in_saturday(cls, **_):
        """if the execution is in saturday"""
        return _is_saturday_in_israel()

    @classmethod
    def failire_valid(cls, when_date=None, utilize_date_param=False, **_):
        """return true if the parser is stble"""
        return super().failire_valid(
            when_date=when_date, utilize_date_param=utilize_date_param
        ) or cls.executed_in_saturday(when_date=when_date)


class CityMarketGivataim(FullyStable):
    """Netiv Hased is stablity"""

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
            super().failire_valid(when_date=when_date)
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
    def searching_for_update_promo(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return files_types and files_types == [FileTypesFilters.PROMO_FILE.name]

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return super().failire_valid(
            when_date=when_date
        ) or cls.searching_for_update_promo(files_types=files_types)


class CityMarketKiratGat(FullyStable):
    """Netiv Hased is stablity"""

    @classmethod
    def searching_for_update_promo_full(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return files_types and files_types == [FileTypesFilters.PROMO_FULL_FILE.name]

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return super().failire_valid(
            when_date=when_date
        ) or cls.searching_for_update_promo_full(files_types=files_types)


class DoNotPublishStores(FullyStable):
    """stablity for chains that doesn't pubish stores"""

    @classmethod
    def searching_for_store_full(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return files_types and files_types == [FileTypesFilters.STORE_FILE.name]

    @classmethod
    def failire_valid(
        cls, when_date=None, files_types=None, utilize_date_param=True, **_
    ):
        """return true if the parser is stble"""
        return super().failire_valid(
            when_date=when_date,
            files_types=files_types,
            utilize_date_param=utilize_date_param,
        ) or cls.searching_for_store_full(files_types=files_types)


class DoNotPublishPromo(FullyStable):
    """stablity for chains that doesn't pubish stores"""

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
        return super().failire_valid(
            when_date=when_date,
            files_types=files_types,
            utilize_date_param=utilize_date_param,
        ) or cls.searching_for_promo_full(files_types=files_types)


class ScraperStability(Enum):
    """tracker for the stablity of the scraper"""

    COFIX = DoNotPublishStores
    NETIV_HASED = NetivHased
    QUIK = DoNotPublishStores
    SALACH_DABACH = DoNotPublishStores
    # CITY_MARKET_GIVATAYIM = CityMarketGivataim
    CITY_MARKET_KIRYATONO = CityMarketKiratOno
    CITY_MARKET_KIRYATGAT = CityMarketKiratGat
    MESHMAT_YOSEF_1 = DoNotPublishPromo
    YOHANANOF = DoNotPublishStores

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

        return stabler.failire_valid(
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            when_date=when_date,
            utilize_date_param=utilize_date_param,
        )
