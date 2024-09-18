from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class Yohananof(Cerberus):
    """scraper for yohananof"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.YOHANANOF,
            chain_id="7290803800003",
            folder_name=folder_name,
            ftp_username="yohananof",
        )
