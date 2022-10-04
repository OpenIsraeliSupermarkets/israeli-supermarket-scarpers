from il_supermarket_scarper.engines import Cerberus


class FreshMarketAndSuperDosh(Cerberus):
    """scraper for fresh market and super dush"""

    def __init__(self, folder_name=None):
        super().__init__(
            "Super Dosh",
            chain_id="7290876100000",
            folder_name=folder_name,
            ftp_username="freshmarket",
        )
