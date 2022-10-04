from il_supermarket_scarper.engines.publishprice import PublishPrice


class YaynotBitan(PublishPrice):
    """scaper for yaynot beitan"""

    def __init__(self, folder_name=None):
        super().__init__(
            "ybitan",
            chain_id="7290725900003",
            site_infix="ybitan",
            folder_name=folder_name,
        )
