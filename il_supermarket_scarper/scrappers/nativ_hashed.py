from il_supermarket_scarper.engines.web import WebBase
from il_supermarket_scarper.utils import _is_saturday_in_israel, _is_holiday_in_israel


class NetivHased(WebBase):
    """scraper for nativ Hased"""

    def __init__(self, folder_name=None):
        super().__init__(
            "Netiv Hased",
            chain_id="7290058160839",
            url="http://141.226.203.152/",
            folder_name=folder_name,
        )

    def _is_validate_scraper_found_no_files(
        self, limit=None, files_types=None, store_id=None, only_latest=False
    ):
        # no data on shabat
        return _is_saturday_in_israel() or _is_holiday_in_israel()
