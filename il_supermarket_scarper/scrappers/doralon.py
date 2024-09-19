from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class DorAlon(Cerberus):
    """scraper for dor alon"""

    def __init__(self, folder_name=None):
        super().__init__(
            folder_name=folder_name,
            chain=DumpFolderNames.DOR_ALON,
            chain_id="7290492000005",
            ftp_username="doralon",
        )
