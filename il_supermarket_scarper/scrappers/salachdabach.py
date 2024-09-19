from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class SalachDabach(Cerberus):
    """scraper for salach dabach"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.SALACH_DABACH,
            chain_id="7290526500006",
            folder_name=folder_name,
            ftp_username="SalachD",
            ftp_password="12345",
        )
