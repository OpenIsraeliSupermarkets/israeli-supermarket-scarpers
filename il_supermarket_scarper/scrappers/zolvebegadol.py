from il_supermarket_scarper.engines import Bina
from il_supermarket_scarper.utils import DumpFolderNames


class ZolVeBegadol(Bina):
    """scraper dfor zol-ve-begodol"""

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            chain=DumpFolderNames.ZOL_VEBEGADOL,
            chain_id="7290058173198",
            url_perfix="zolvebegadol",
            file_output=file_output,
            status_database=status_database,
        )
