from il_supermarket_scarper.engines.publishprice import PublishPrice
from il_supermarket_scarper.utils import DumpFolderNames


class YaynotBitanAndCarrefour(PublishPrice):
    """scaper for yaynot beitan"""

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            chain=DumpFolderNames.YAYNO_BITAN_AND_CARREFOUR,
            chain_id="7290055700007",
            site_infix="carrefour",
            file_output=file_output,
            status_database=status_database,
        )
