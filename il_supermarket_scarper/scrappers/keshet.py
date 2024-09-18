from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class Keshet(Cerberus):
    """scaper for keshet tamim"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.KESHET,
            chain_id="7290785400000",
            folder_name=folder_name,
            ftp_username="Keshet",
        )
