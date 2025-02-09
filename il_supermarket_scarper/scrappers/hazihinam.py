import urllib.parse
import datetime
from il_supermarket_scarper.engines import MultiPageWeb
from il_supermarket_scarper.utils import DumpFolderNames, FileTypesFilters, _now

# class HaziHinam(Cerberus):
#     """scrper fro hazi hinam"""

#     def __init__(self, folder_name=None):
#         super().__init__(
#             chain=DumpFolderNames.HAZI_HINAM,
#             chain_id="7290700100008",
#             folder_name=folder_name,
#             ftp_username="HaziHinam",
#         )


class HaziHinam(MultiPageWeb):
    """scrper fro hazi hinam"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.HAZI_HINAM,
            chain_id="7290700100008",
            url="https://shop.hazi-hinam.co.il/Prices",
            folder_name=folder_name,
            total_page_xpath="(//li[contains(concat(' ', normalize-space(@class), ' '),"
            + "' pagination-item ')])[last()]/a/@href",
            total_pages_pattern=r"\d+",
            page_argument="&p",
        )

    def collect_files_details_from_page(self, html):
        """collect the details deom one page"""
        links = []
        filenames = []
        for link in html.xpath("//table/tbody/tr"):
            links.append(link.xpath("td[6]/a/@href")[0])
            filenames.append(link.xpath("td[3]")[0].text.strip() + ".xml.gz")
        return links, filenames

    def get_file_types_id(self, files_types=None):
        """get the file type id"""
        if files_types is None or files_types == FileTypesFilters.all_types():
            return [{"t": "null", "f": "null"}]

        types = []
        for ftype in files_types:
            if ftype == FileTypesFilters.STORE_FILE.name:
                types.append({"t": "3", "f": "null"})
            if ftype == FileTypesFilters.PRICE_FILE.name:
                types.append({"t": "1", "f": "null"})
            if ftype == FileTypesFilters.PROMO_FILE.name:
                types.append({"t": "2", "f": "null"})
            if ftype == FileTypesFilters.PRICE_FULL_FILE.name:
                types.append({"t": "1", "f": "null"})
            if ftype == FileTypesFilters.PROMO_FULL_FILE.name:
                types.append({"t": "2", "f": "null"})
        return types

    def build_params(self, files_types=None, store_id=None, when_date=None):
        """build the params for the request"""

        all_params = []
        for type_params in self.get_file_types_id(files_types):

            # filtering store is not supported
            # if store_id:
            #     params["s"] = "null"
            if when_date and isinstance(when_date, datetime.datetime):
                all_params.append({"d": when_date.strftime("%Y-%m-%d"), **type_params})
            else:
                all_params.append({"d": _now().strftime("%Y-%m-%d"), **type_params})
                all_params.append(
                    {
                        "d": (_now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
                        **type_params,
                    }
                )

        return ["?" + urllib.parse.urlencode(params) for params in all_params]
