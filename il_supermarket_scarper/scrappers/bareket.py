from il_supermarket_scarper.engines import Bina
from il_supermarket_scarper.utils import DumpFolderNames


class Bareket(Bina):
    """scarper for bareket"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.BAREKET,
            chain_id="7290875100001",
            url_perfix="superbareket",
            folder_name=folder_name,
        )
