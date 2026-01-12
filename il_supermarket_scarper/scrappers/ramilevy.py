from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class RamiLevy(Cerberus):
    """scaper for rami levi"""

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            chain=DumpFolderNames.RAMI_LEVY,
            chain_id="7290058140886",
            file_output=file_output, status_database=status_database,
            ftp_username="RamiLevi",
            max_threads=10,
        )
