from enum import Enum
import datetime
from il_supermarket_scarper.utils import _is_saturday_in_israel


class FullyStable:
    """fully stable is stablity"""

    @staticmethod
    def failire_valid(**_):
        """return true if the parser is stble"""
        return False


class NetivHased(FullyStable):
    """Netiv Hased is stablity"""

    @staticmethod
    def failire_valid(when_date=None, **_):
        """return true if the parser is stble"""
        return when_date and _is_saturday_in_israel(when_date)


class SuperYuda(FullyStable):
    """Super Yuda is stablity"""

    @staticmethod
    def failire_valid(when_date=None, **_):
        return when_date and when_date > datetime.date(2024, 9, 26)


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

        return stabler.failire_valid(limit, files_types, store_id, when_date)
