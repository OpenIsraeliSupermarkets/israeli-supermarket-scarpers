from il_supermarket_scarper.engines.web import WebBase
from il_supermarket_scarper.utils import DumpFolderNames


# possible: NetivHased are down in Shabatz
class NetivHased(WebBase):
    """scraper for nativ Hased"""

    utilize_date_param = False

    def __init__(self, streaming_config=None):
        super().__init__(
            chain=DumpFolderNames.NETIV_HASED,
            chain_id="7290058160839",
            url="http://141.226.203.152/",
            streaming_config=streaming_config
        )
