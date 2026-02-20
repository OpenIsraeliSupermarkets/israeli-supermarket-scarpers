from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class Osherad(Cerberus):
    """scaper for osher ad"""

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            chain=DumpFolderNames.OSHER_AD,
            chain_id="7290103152017",
            file_output=file_output,
            status_database=status_database,
            ftp_username="osherad",
        )
