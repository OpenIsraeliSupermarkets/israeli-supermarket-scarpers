from il_supermarket_scarper.engines.web import WebBase
from il_supermarket_scarper.utils import _is_saturday_in_israel, _is_holiday_in_israel


class NetivHasef(WebBase):
    """scraper for nativ hasef"""

    def __init__(self, folder_name=None):
        super().__init__(
            "Netiv Hasef",
            chain_id="7290058160839",
            url="http://141.226.222.202/",
            folder_name=folder_name,
        )

    def is_validate_scraper_found_no_files(self, limit=None, files_types=None):
        # no data on shabat
        result = super().is_validate_scraper_found_no_files(
            limit=limit, files_types=files_types
        )
        return result or _is_saturday_in_israel() or _is_holiday_in_israel()
