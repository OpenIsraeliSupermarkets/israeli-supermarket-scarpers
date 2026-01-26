from il_supermarket_scarper.engines import Matrix
from il_supermarket_scarper.utils import DumpFolderNames


class MahsaniAShuk(Matrix):
    """scraper for masani hsuk"""

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            chain=DumpFolderNames.MAHSANI_ASHUK,
            chain_id=["7290661400001", "7290633800006"],
            file_output=file_output,
            status_database=status_database,
            chain_hebrew_name="מחסני השוק",
        )
