from il_supermarket_scarper.engines import Cerberus


class DorAlon(Cerberus):
    """scraper for dor alon"""

    def __init__(self, folder_name=None):
        super().__init__(
            folder_name=folder_name,
            chain="Dor Alon",
            chain_id="7290492000005",
            ftp_username="doralon",
        )
