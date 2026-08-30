from il_supermarket_scarper.engines.web import WebBase
from il_supermarket_scarper.utils import DumpFolderNames


# NetivHased: still on gov.il; URL must match cpfta_prices_regulations
class NetivHased(WebBase):
    """scraper for nativ Hased"""

    utilize_date_param = False

    def __init__(self, file_output=None, status_database=None):
        super().__init__(
            chain=DumpFolderNames.NETIV_HASED,
            chain_id="7290058160839",
            url="https://app.netiv-hesed.com/",
            file_output=file_output,
            status_database=status_database,
        )
