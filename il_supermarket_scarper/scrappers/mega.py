from il_supermarket_scarper.engines.publishprice import PublishPrice


class Mega(PublishPrice):
    """scraper for mege"""

    def __init__(self, folder_name=None):
        super().__init__(
            "mega", chain_id="7290055700007", site_infix="mega", folder_name=folder_name
        )
