from il_supermarket_scarper.engines import Bina
from il_supermarket_scarper.utils import DumpFolderNames


class ZolVeBegadol(Bina):
    """scraper dfor zol-ve-begodol"""

    def __init__(self, streaming_config=None):
        super().__init__(
            chain=DumpFolderNames.ZOL_VEBEGADOL,
            chain_id="7290058173198",
            url_perfix="zolvebegadol",
            streaming_config=streaming_config,
        )
