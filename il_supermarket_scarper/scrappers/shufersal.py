from il_supermarket_scarper.engines import MultiPageWeb
from il_supermarket_scarper.utils import DumpFolderNames


class Shufersal(MultiPageWeb):
    """scaper for shufersal"""

    def __init__(self, folder_name=None):
        super().__init__(
            url="https://prices.shufersal.co.il/",
            chain=DumpFolderNames.SHUFERSAL,
            chain_id="7290027600007",
            folder_name=folder_name,
        )
