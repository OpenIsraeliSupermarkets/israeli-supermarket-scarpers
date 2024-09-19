from il_supermarket_scarper.engines import Bina
from il_supermarket_scarper.utils import DumpFolderNames


class ShefaBarcartAshem(Bina):
    """scraper for shefa berkat ashem"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.SHEFA_BARCART_ASHEM,
            chain_id="7290058134977",
            url_perfix="shefabirkathashem",
            folder_name=folder_name,
        )
