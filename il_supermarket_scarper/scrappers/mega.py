from il_supermarket_scarper.engines.publishprice import PublishPrice
from il_supermarket_scarper.utils import DumpFolderNames


# removed : 1.7.2025
class Mega(PublishPrice):
    """scraper for mege"""

    def __init__(self, streaming_config=None):
        super().__init__(
            chain=DumpFolderNames.MEGA,
            chain_id="7290055700007",
            site_infix="mega",
            streaming_config=streaming_config
        )
