from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class SalachDabach(Cerberus):
    """scraper for salach dabach"""

    def __init__(self, streaming_config=None):
        super().__init__(
            chain=DumpFolderNames.SALACH_DABACH,
            chain_id="7290526500006",
            ftp_username="SalachD",
            ftp_password="12345",
            streaming_config=streaming_config
        )
