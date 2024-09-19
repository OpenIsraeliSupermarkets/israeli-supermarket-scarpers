from il_supermarket_scarper.engines import Bina
from il_supermarket_scarper.utils import DumpFolderNames


class KingStore(Bina):
    """scraper for king store"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.KING_STORE,
            chain_id="7290058108879",
            url_perfix="kingstore",
            folder_name=folder_name,
        )
