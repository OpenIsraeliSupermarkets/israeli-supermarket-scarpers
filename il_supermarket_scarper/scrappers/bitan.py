from il_supermarket_scarper.engines.publishprice import PublishPrice
from il_supermarket_scarper.utils import DumpFolderNames


class YaynotBitanAndCarrefour(PublishPrice):
    """scaper for yaynot beitan"""

    def __init__(self, streaming_config=None):
        super().__init__(
            chain=DumpFolderNames.YAYNO_BITAN_AND_CARREFOUR,
            chain_id="7290055700007",
            site_infix="carrefour",
            streaming_config=streaming_config
        )
