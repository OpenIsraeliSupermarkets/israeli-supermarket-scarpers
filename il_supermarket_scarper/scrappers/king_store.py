from il_supermarket_scarper.engines import Bina
from il_supermarket_scarper.utils import DumpFolderNames


class KingStore(Bina):
    """scraper for king store"""

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            chain=DumpFolderNames.KING_STORE,
            chain_id="7290058108879",
            url_perfix="kingstore",
            file_output=file_output,
            status_database=status_database,
        )
