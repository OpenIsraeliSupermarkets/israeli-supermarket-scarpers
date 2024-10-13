from il_supermarket_scarper.engines import Bina
from il_supermarket_scarper.utils import DumpFolderNames


class SuperYuda(Bina):
    """scraper for super yuda"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.SUPER_YUDA,
            chain_id=["7290058198450", "7290058177776"],
            url_perfix="Paz",
            folder_name=folder_name,
        )
