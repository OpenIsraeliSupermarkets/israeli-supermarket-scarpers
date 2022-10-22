from il_supermarket_scarper.engines import Cerberus


class StopMarket(Cerberus):
    """scraper for stop market"""

    def __init__(self, folder_name=None):
        super().__init__(
            "Stop Market",
            chain_id=[
                "72906390",
                "7290639000004",
            ],  # in store files for some reason the store id is only 72906390
            folder_name=folder_name,
            ftp_username="Stop_Market",
        )
