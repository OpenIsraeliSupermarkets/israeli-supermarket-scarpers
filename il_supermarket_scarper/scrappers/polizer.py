from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class Polizer(Cerberus):
    """scarper for polizer"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.POLIZER,
            chain_id="7291059100008",
            folder_name=folder_name,
            ftp_username="politzer",
        )
