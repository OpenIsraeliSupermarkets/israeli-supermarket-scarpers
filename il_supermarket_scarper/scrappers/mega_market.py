from il_supermarket_scarper.engines.publishprice import PublishPrice


class MegaMarket(PublishPrice):
    """scaper for mege market"""

    def __init__(self, folder_name=None):
        super().__init__(
            "mega-market",
            chain_id="7290055700014",
            site_infix="mega-market",
            folder_name=folder_name,
        )
