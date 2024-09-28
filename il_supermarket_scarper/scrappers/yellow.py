from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class Yellow(Cerberus):
    """scraper for yellow"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.YELLOW,
            chain_id="7290644700005",
            folder_name=folder_name,
            ftp_username="Paz_bo",
            ftp_password="paz468",
            max_threads=10,
        )
