import urllib.parse

from il_supermarket_scarper.engines import Bina, MultiPageWeb
from il_supermarket_scarper.utils import DumpFolderNames, FileTypesFilters


class CityMarketGivatayim(Bina):
    """scraper for city market givatayim"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.CITY_MARKET_GIVATAYIM,
            chain_id="5359000000000",
            url_perfix="citymarketgivatayim",
            folder_name=folder_name,
        )


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
            page_argument="?p",
        )

    def collect_files_details_from_page(self, html):
        """collect the details deom one page"""
        links = []
        filenames = []
        for link in html.xpath("//table/tbody/tr"):
            links.append(link.xpath("td[7]/a/@href")[0] + ".xml.gz")
            filenames.append(link.xpath("td[3]")[0].text.strip())
        return links, filenames

    def get_file_types_id(self, files_types=None):
        """get the file type id"""
        if files_types is None:
            return ""

        types = []
        for ftype in files_types:
            if ftype == FileTypesFilters.STORE_FILE.name:
                types.append({"t": 3})
            if ftype == FileTypesFilters.PRICE_FILE.name:
                types.append({"t": "1", "f": "0"})
            if ftype == FileTypesFilters.PROMO_FILE.name:
                types.append({"t": "2", "f": "0"})
            if ftype == FileTypesFilters.PRICE_FULL_FILE.name:
                types.append({"t": "1", "f": "1"})
            if ftype == FileTypesFilters.PROMO_FULL_FILE.name:
                types.append({"t": "2", "f": "1"})
        return types[0]

    def build_params(self, files_types=None, store_id=None, when_date=None):
        """build the params for the request"""
        assert (
            files_types is None or len(files_types) == 1
        ), "SuperPharm supports only one file type"

        params = {"d": "", "s": ""}

        if store_id:
            params["s"] = store_id
        if when_date:
            params["d"] = when_date.strftime("%Y-%m-%d")
        if files_types:
            params = {**params, **self.get_file_types_id(files_types)}

        return "?" + urllib.parse.urlencode(params)