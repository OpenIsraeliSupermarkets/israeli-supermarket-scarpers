from il_supermarket_scarper.engines import Bina
from il_supermarket_scarper.utils import DumpFolderNames


class ShefaBarcartAshem(Bina):
    """scraper for shefa berkat ashem"""

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            chain=DumpFolderNames.SHEFA_BARCART_ASHEM,
            chain_id="7290058134977",
            url_perfix="shefabirkathashem",
            file_output=file_output,
            status_database=status_database,
        )
