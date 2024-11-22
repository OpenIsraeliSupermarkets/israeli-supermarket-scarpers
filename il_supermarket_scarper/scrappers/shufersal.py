import urllib.parse

from il_supermarket_scarper.engines import MultiPageWeb
from il_supermarket_scarper.utils import DumpFolderNames, FileTypesFilters


class Shufersal(MultiPageWeb):
    """scaper for shufersal"""

    utilize_date_param = False

    def __init__(self, folder_name=None):
        super().__init__(
            url="https://prices.shufersal.co.il/",
            total_page_xpath="""//*[@id="gridContainer"]/table/tfoot/tr/td/a[6]/@href""",
            total_pages_pattern=r"[?&]page=([0-9]+)",
            chain=DumpFolderNames.SHUFERSAL,
            chain_id="7290027600007",
            folder_name=folder_name,
            page_argument="&page",
        )

    def get_file_types_id(self, files_types=None):
        """get the file type id"""
        if files_types is None:
            return ["0"]

        types = []
        for ftype in files_types:
            if ftype == FileTypesFilters.STORE_FILE.name:
                types.append("5")
            if ftype == FileTypesFilters.PRICE_FILE.name:
                types.append("1")
            if ftype == FileTypesFilters.PROMO_FILE.name:
                types.append("3")
            if ftype == FileTypesFilters.PRICE_FULL_FILE.name:
                types.append("2")
            if ftype == FileTypesFilters.PROMO_FULL_FILE.name:
                types.append("4")
        return types

    def build_params(self, files_types=None, store_id=None, when_date=None):
        """build the params for the request"""
        params = {"catID": ",".join(self.get_file_types_id(files_types))}

        if store_id:
            params["storeId"] = store_id
        return [f"/FileObject/UpdateCategory?{urllib.parse.urlencode(params)}"]
