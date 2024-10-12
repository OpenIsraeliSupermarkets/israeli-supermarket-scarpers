from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class TivTaam(Cerberus):
    """scraper for tiv taam"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.TIV_TAAM,
            chain_id="7290873255550",
            folder_name=folder_name,
            ftp_username="TivTaam",
        )
