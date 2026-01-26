from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class StopMarket(Cerberus):
    """scraper for stop market"""

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            chain=DumpFolderNames.STOP_MARKET,
            chain_id=[
                "72906390",
                "7290639000004",
            ],  # in store files for some reason the store id is only 72906390
            file_output=file_output,
            status_database=status_database,
            ftp_username="Stop_Market",
        )
