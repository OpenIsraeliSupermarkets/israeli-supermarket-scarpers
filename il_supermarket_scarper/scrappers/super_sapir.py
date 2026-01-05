from il_supermarket_scarper.engines import Bina
from il_supermarket_scarper.utils import DumpFolderNames


class SuperSapir(Bina):
    """scaper for super sapir"""

    def __init__(self, file_output=None):
        super().__init__(
            chain=DumpFolderNames.SUPER_SAPIR,
            chain_id="7290058156016",
            url_perfix="supersapir",
            file_output=file_output,
        )
