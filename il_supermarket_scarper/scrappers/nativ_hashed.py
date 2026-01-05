from il_supermarket_scarper.engines.web import WebBase
from il_supermarket_scarper.utils import DumpFolderNames


# possible: NetivHased are down in Shabatz
class NetivHased(WebBase):
    """scraper for nativ Hased"""

    utilize_date_param = False

    def __init__(self, file_output=None):
        super().__init__(
            chain=DumpFolderNames.NETIV_HASED,
            chain_id="7290058160839",
            url="http://141.226.203.152/",
            file_output=file_output,
        )
