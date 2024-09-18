from il_supermarket_scarper.engines import Bina
from il_supermarket_scarper.utils import DumpFolderNames


class Maayan2000(Bina):
    """scaper for maayan 2000"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.MAAYAN_2000,
            chain_id="7290058159628",
            url_perfix="maayan2000",
            folder_name=folder_name,
        )
