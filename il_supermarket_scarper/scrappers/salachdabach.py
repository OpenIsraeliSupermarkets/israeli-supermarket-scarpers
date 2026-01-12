from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class SalachDabach(Cerberus):
    """scraper for salach dabach"""

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            chain=DumpFolderNames.SALACH_DABACH,
            chain_id="7290526500006",
            file_output=file_output, status_database=status_database,
            ftp_username="SalachD",
            ftp_password="12345",
        )
