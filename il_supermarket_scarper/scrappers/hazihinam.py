from il_supermarket_scarper.engines import Cerberus
from il_supermarket_scarper.utils import DumpFolderNames


class HaziHinam(Cerberus):
    """scrper fro hazi hinam"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.HAZI_HINAM,
            chain_id="7290700100008",
            folder_name=folder_name,
            ftp_username="HaziHinam",
        )
