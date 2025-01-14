from il_supermarket_scarper.engines.publishprice import PublishPrice
from il_supermarket_scarper.utils import DumpFolderNames


# @FlakyScraper
class Quik(PublishPrice):
    """scaper for quik"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.QUIK,
            chain_id="7291029710008",
            site_infix="quik",
            folder_name=folder_name,
        )
