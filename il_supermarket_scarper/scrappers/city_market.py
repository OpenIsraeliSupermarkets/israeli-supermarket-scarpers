import urllib.parse
import datetime
from il_supermarket_scarper.engines import Bina, MultiPageWeb
from il_supermarket_scarper.utils import DumpFolderNames, FileTypesFilters


# removed on 28.02.2025
class CityMarketGivatayim(Bina):
    """scraper for city market givatayim"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.CITY_MARKET_GIVATAYIM,
            chain_id="5359000000000",
            url_perfix="citymarketgivatayim",
            folder_name=folder_name,
        )


# removed on 28.10.2024
class CityMarketKirtatOno(Bina):
    """scraper for city market givatayim"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.CITY_MARKET_KIRYATONO,
            chain_id="5359000000000",
            url_perfix="citymarketkiryatono",
            folder_name=folder_name,
        )


class CityMarketKiryatGat(Bina):
    """scraper for city market givatayim"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.CITY_MARKET_KIRYATGAT,
            chain_id="7290058266241",
            url_perfix="citymarketkiryatgat",
            folder_name=folder_name,
        )


class CityMarketShops(MultiPageWeb):
    """scraper for city market givatayim"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.CITY_MARKET_SHOPS,
            chain_id="7290000000003",
            url="http://www.citymarket-shops.co.il/",
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
            links.append(self.url + link.xpath("td[7]/a/@href")[0])
            filenames.append(link.xpath("td[3]")[0].text.strip() + ".xml.gz")
        return links, filenames

    def get_file_types_id(self, files_types=None):
        """get the file type id"""
        if files_types is None or files_types == FileTypesFilters.all_types():
            return [{"t": "", "f": ""}]

        types = []
        for ftype in files_types:
            if ftype == FileTypesFilters.STORE_FILE.name:
                types.append({"t": 3, "f": ""})
            if ftype == FileTypesFilters.PRICE_FILE.name:
                types.append({"t": "1", "f": "0"})
            if ftype == FileTypesFilters.PROMO_FILE.name:
                types.append({"t": "2", "f": "0"})
            if ftype == FileTypesFilters.PRICE_FULL_FILE.name:
                types.append({"t": "1", "f": "1"})
            if ftype == FileTypesFilters.PROMO_FULL_FILE.name:
                types.append({"t": "2", "f": "1"})
        return types

    def build_params(self, files_types=None, store_id=None, when_date=None):
        """build the params for the request"""

        all_params = []
        for type_params in self.get_file_types_id(files_types):
            params = {"d": "", "s": ""}

            if store_id:
                params["s"] = str(store_id).zfill(3)
            if when_date and isinstance(when_date, datetime.datetime):
                params["d"] = when_date.strftime("%Y-%m-%d")
            if files_types:
                params = {**params, **type_params}
            all_params.append(params)

        return ["?" + urllib.parse.urlencode(params) for params in all_params]
