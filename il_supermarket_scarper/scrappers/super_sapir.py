from il_supermarket_scarper.engines import Bina
from il_supermarket_scarper.utils import DumpFolderNames


class SuperSapir(Bina):
    """scaper for super sapir"""

    def __init__(self, streaming_config=None):
        super().__init__(
            chain=DumpFolderNames.SUPER_SAPIR,
            chain_id="7290058156016",
            url_perfix="supersapir",
            streaming_config=streaming_config,
        )
