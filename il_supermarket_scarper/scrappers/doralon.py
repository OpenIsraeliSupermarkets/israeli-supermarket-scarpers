from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class DorAlon(Cerberus):
    """scraper for dor alon"""

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            file_output=file_output, status_database=status_database,
            chain=DumpFolderNames.DOR_ALON,
            chain_id=["7290492000005", "729049000005"],
            ftp_username="doralon",
        )
