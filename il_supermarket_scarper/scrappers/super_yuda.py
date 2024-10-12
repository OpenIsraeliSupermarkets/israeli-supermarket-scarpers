import datetime
from il_supermarket_scarper.engines import Bina
from il_supermarket_scarper.utils import DumpFolderNames, Logger


class SuperYuda(Bina):
    """scraper for super yuda"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.SUPER_YUDA,
            chain_id=["7290058198450", "7290058177776"],
            url_perfix="Paz",
            folder_name=folder_name,
        )

    def _is_validate_scraper_found_no_files(
        self, limit=None, files_types=None, store_id=None, when_date=None
    ):

        date_stoped_updateing = (
            when_date is not None
            and isinstance(when_date, datetime.datetime)
            and when_date.date() > datetime.date(2024, 9, 26)
        )

        if date_stoped_updateing:
            Logger.warning("SuperYuda stoped updating the site after 12/10/2024")

        return (
            super()._is_validate_scraper_found_no_files(
                limit, files_types, store_id, when_date
            )
            or date_stoped_updateing
        )
