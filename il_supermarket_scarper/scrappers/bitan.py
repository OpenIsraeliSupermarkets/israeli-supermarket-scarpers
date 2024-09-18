from il_supermarket_scarper.engines.publishprice import PublishPrice
from il_supermarket_scarper.utils import DumpFolderNames


class YaynotBitan(PublishPrice):
    """scaper for yaynot beitan"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.YAYNO_BITAN,
            chain_id="7290725900003",
            site_infix="ybitan",
            folder_name=folder_name,
        )
