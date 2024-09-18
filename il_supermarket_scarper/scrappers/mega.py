from il_supermarket_scarper.engines.publishprice import PublishPrice
from il_supermarket_scarper.utils import DumpFolderNames


class Mega(PublishPrice):
    """scraper for mege"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.MEGA,
            chain_id="7290055700007",
            site_infix="mega",
            folder_name=folder_name,
        )
