from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class RamiLevy(Cerberus):
    """scaper for rami levi"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.RAMI_LEVY,
            chain_id="7290058140886",
            folder_name=folder_name,
            ftp_username="RamiLevi",
            max_threads=10,
        )
