from il_supermarket_scarper.engines.web import WebBase
from il_supermarket_scarper.utils import _is_saturday_in_israel

class NetivHasef(WebBase):
    """ scraper for nativ hasef """

    def __init__(self, folder_name=None):
        super().__init__("Netiv Hasef", chain_id="7290058160839", 
                url="http://141.226.222.202/", folder_name=folder_name)


    def _validate_scraper_found_no_files(self):
        # no data on shabat
        return not _is_saturday_in_israel()
