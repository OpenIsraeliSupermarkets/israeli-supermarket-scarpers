from il_supermarket_scarper.utils import _is_saturday_in_israel
from enum import Enum
import datetime


class NetivHased:

    @staticmethod
    def failire_valid(limit=None, files_types=None, store_id=None, when_date=None):
        return _is_saturday_in_israel(when_date)


class SuperYuda:

    @staticmethod
    def failire_valid(limit=None, files_types=None, store_id=None, when_date=None):
        return when_date > datetime.date(2024, 9, 26)


class FullyStable:

    @staticmethod
    def failire_valid(limit=None, files_types=None, store_id=None, when_date=None):
        return False


class ScraperStability(Enum):

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
