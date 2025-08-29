from il_supermarket_scarper.engines import Matrix
from il_supermarket_scarper.utils import DumpFolderNames


class MahsaniAShuk(Matrix):
    """scraper for masani hsuk"""

    def __init__(self, streaming_config=None):
        super().__init__(
            chain=DumpFolderNames.MAHSANI_ASHUK,
            chain_id=["7290661400001", "7290633800006"],
            chain_hebrew_name="מחסני השוק",
            streaming_config=streaming_config
        )
