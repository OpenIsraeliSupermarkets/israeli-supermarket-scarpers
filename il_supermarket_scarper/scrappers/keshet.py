from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class Keshet(Cerberus):
    """scaper for keshet tamim"""

    def __init__(self, file_output=None):
        super().__init__(
            chain=DumpFolderNames.KESHET,
            chain_id="7290785400000",
            file_output=file_output,
            ftp_username="Keshet",
        )
