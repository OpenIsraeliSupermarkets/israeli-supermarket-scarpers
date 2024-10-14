from enum import Enum
from il_supermarket_scarper.utils import _is_saturday_in_israel, _now, FileTypesFilters


class FullyStable:
    """fully stable is stablity"""

    @classmethod
    def executes_between_midnight_and_morning_and_requested_today(
        cls, when_date=None, **_
    ):
        """it is stable if the execution is between midnight
        and morning and the requested date is today fails"""
        execution_time = _now()
        return (
            when_date
            and execution_time.hour >= 0
            and execution_time.hour < 8
            and when_date.date() == execution_time.date()
        )

    @classmethod
    def failire_valid(cls, when_date=None, **_):
        """return true if the parser is stble"""

        return cls.executes_between_midnight_and_morning_and_requested_today(
            when_date=when_date
        )


class SuperFlaky(FullyStable):
    """super flaky is stablity"""

    @classmethod
    def failire_valid(cls, when_date=None, **_):
        return True


class Quik(FullyStable):
    """define stability for small chain"""

    @classmethod
    def executes_early_morning_ask_for_alot_of_files(cls, limit=None, **_):
        """small chain don't upload many files in the morning"""
        execution_time = _now()
        return limit and execution_time.hour < 12 and limit > 8

    @classmethod
    def executes_looking_for_store(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return files_types and files_types == [FileTypesFilters.STORE_FILE.name]

    @classmethod
    def failire_valid(cls, when_date=None, limit=None, files_types=None, **_):
        """return true if the parser is stble"""
        return (
            super().failire_valid(when_date=when_date)
            or cls.executes_early_morning_ask_for_alot_of_files(limit=limit)
            or cls.executes_looking_for_store(files_types=files_types)
        )


class NetivHased(FullyStable):
    """Netiv Hased is stablity"""

    @classmethod
    def executed_in_saturday(cls, when_date=None, **_):
        """if the execution is in saturday"""
        return when_date and _is_saturday_in_israel(when_date)

    @classmethod
    def failire_valid(cls, when_date=None, **_):
        """return true if the parser is stble"""
        return super().failire_valid(when_date=when_date) or cls.executed_in_saturday(
            when_date=when_date
        )


class SalachDabach(FullyStable):
    """Netiv Hased is stablity"""

    @classmethod
    def searching_for_store(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return files_types and files_types == [FileTypesFilters.STORE_FILE.name]

    @classmethod
    def failire_valid(cls, when_date=None, files_types=None, **_):
        """return true if the parser is stble"""
        return super().failire_valid(when_date=when_date) or cls.searching_for_store(
            files_types=files_types
        )


class CityMarketGivataim(FullyStable):
    """Netiv Hased is stablity"""

    @classmethod
    def searching_for_update_promo(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return files_types and files_types == [FileTypesFilters.PROMO_FILE.name]

    @classmethod
    def failire_valid(cls, when_date=None, files_types=None, **_):
        """return true if the parser is stble"""
        return super().failire_valid(
            when_date=when_date
        ) or cls.searching_for_update_promo(files_types=files_types)


class CityMarketKiratOno(FullyStable):
    """Netiv Hased is stablity"""

    @classmethod
    def searching_for_update_promo(cls, files_types=None, **_):
        """if the execution is in saturday"""
        return files_types and files_types == [FileTypesFilters.PROMO_FILE.name]

    @classmethod
    def failire_valid(cls, when_date=None, files_types=None, **_):
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
    def failire_valid(cls, when_date=None, files_types=None, **_):
        """return true if the parser is stble"""
        return super().failire_valid(
            when_date=when_date
        ) or cls.searching_for_update_promo_full(files_types=files_types)


class ScraperStability(Enum):
    """tracker for the stablity of the scraper"""

    NETIV_HASED = NetivHased
    QUIK = Quik
    SALACH_DABACH = SalachDabach
    CITY_MARKET_GIVATAYIM = CityMarketGivataim
    CITY_MARKET_KIRYATONO = CityMarketKiratOno
    CITY_MARKET_KIRYATGAT = CityMarketKiratGat
    MESHMAT_YOSEF_1 = SuperFlaky

    @classmethod
    def is_validate_scraper_found_no_files(
        cls, scraper_enum, limit=None, files_types=None, store_id=None, when_date=None
    ):
        """return true if its ok the scarper reuturn no enrty"""

        stabler = FullyStable
        if scraper_enum in ScraperStability.__members__:
            stabler = ScraperStability[scraper_enum].value

        return stabler.failire_valid(
            limit=limit, files_types=files_types, store_id=store_id, when_date=when_date
        )
