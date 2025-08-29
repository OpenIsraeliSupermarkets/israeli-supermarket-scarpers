from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class Osherad(Cerberus):
    """scaper for osher ad"""

    def __init__(self, streaming_config=None):
        super().__init__(
            chain=DumpFolderNames.OSHER_AD,
            chain_id="7290103152017",
            ftp_username="osherad",
            streaming_config=streaming_config
        )
