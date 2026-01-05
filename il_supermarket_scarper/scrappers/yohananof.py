from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class Yohananof(Cerberus):
    """scraper for yohananof"""

    def __init__(self, file_output=None):
        super().__init__(
            chain=DumpFolderNames.YOHANANOF,
            chain_id="7290803800003",
            file_output=file_output,
            ftp_username="yohananof",
        )
