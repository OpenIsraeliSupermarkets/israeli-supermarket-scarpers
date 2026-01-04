from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class DorAlon(Cerberus):
    """scraper for dor alon"""

    def __init__(self,streaming_config=None):
        super().__init__(
            chain=DumpFolderNames.DOR_ALON,
            chain_id=["7290492000005", "729049000005"],
            ftp_username="doralon",
            streaming_config=streaming_config
        )
