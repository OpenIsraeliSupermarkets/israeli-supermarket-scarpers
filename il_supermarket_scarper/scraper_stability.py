from enum import Enum
import datetime
from il_supermarket_scarper.utils import _is_saturday_in_israel, _now


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
            and execution_time.hour < 8
            and when_date.date() == execution_time.date()
        )

    @classmethod
    def failire_valid(cls, when_date=None, **_):
        """return true if the parser is stble"""

        return cls.executes_between_midnight_and_morning_and_requested_today(
            when_date=when_date
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


class SuperYuda(FullyStable):
    """Super Yuda is stablity"""

    @classmethod
    def executed_after_last_data_upload(cls, when_date=None, **_):
        """super yuda stop uploading data after 2024-09-26"""
        return when_date and when_date > datetime.date(2024, 9, 26)

    @classmethod
    def failire_valid(cls, when_date=None, **_):

        return super().failire_valid(
            when_date=when_date
        ) or cls.executed_after_last_data_upload(when_date=when_date)


class ScraperStability(Enum):
    """tracker for the stablity of the scraper"""

    NETIV_HASED = NetivHased
    SUPER_YUDA = SuperYuda

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
