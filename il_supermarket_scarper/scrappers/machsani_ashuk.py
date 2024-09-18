from il_supermarket_scarper.engines import Matrix
from il_supermarket_scarper.utils import DumpFolderNames


class MahsaniAShuk(Matrix):
    """scraper for masani hsuk"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.MAHSANI_ASHUK,
            chain_hebrew_name="מחסני השוק",
            chain_id=["7290661400001", "7290633800006"],
            folder_name=folder_name,
        )
