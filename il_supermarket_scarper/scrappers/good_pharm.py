from il_supermarket_scarper.engines import Bina
from il_supermarket_scarper.utils import DumpFolderNames


class GoodPharm(Bina):
    """scarper from good pharm"""

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            chain=DumpFolderNames.GOOD_PHARM,
            chain_id="7290058197699",
            url_perfix="goodpharm",
            file_output=file_output,
            status_database=status_database,
        )
