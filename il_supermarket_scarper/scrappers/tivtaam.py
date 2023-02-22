from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import (
    _is_saturday_in_israel,
    _is_holiday_in_israel,
    FileTypesFilters,
)


class TivTaam(Cerberus):
    """scraper for tiv taam"""

    def __init__(self, folder_name=None):
        super().__init__(
            "Tiv Taam",
            chain_id="7290873255550",
            folder_name=folder_name,
            ftp_username="TivTaam",
        )

    def is_validate_scraper_found_no_files(
        self, limit=None, files_types=None, store_id=None, only_latest=False
    ):
        return (
            _is_saturday_in_israel()
            or _is_holiday_in_israel()
            or files_types
            == [
                FileTypesFilters.PRICE_FILE.name
            ]  # some wendsday, there is only pricefull files.
        )
