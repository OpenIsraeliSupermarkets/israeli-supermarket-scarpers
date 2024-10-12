from il_supermarket_scarper.engines.web import WebBase
from il_supermarket_scarper.utils import DumpFolderNames, _is_saturday_in_israel


# possible: NetivHased are down in Shabatz
class NetivHased(WebBase):
    """scraper for nativ Hased"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.NETIV_HASED,
            chain_id="7290058160839",
            url="http://141.226.203.152/",
            folder_name=folder_name,
        )

    def _is_validate_scraper_found_no_files(
        self, limit=None, files_types=None, store_id=None, when_date=None
    ):
        return (
            super()._is_validate_scraper_found_no_files(
                limit, files_types, store_id, when_date
            )
            or _is_saturday_in_israel()
        )
