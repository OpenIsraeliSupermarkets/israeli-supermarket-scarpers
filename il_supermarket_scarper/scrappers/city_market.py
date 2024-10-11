from il_supermarket_scarper.engines import Bina, MultiPageWeb
from il_supermarket_scarper.utils import DumpFolderNames


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
            page_argument="p",
        )

    def collect_files_details_from_page(self, html):
        """collect the details deom one page"""
        links = []
        filenames = []
        for link in html.xpath("//table/tbody/tr"):
            links.append(link.xpath("td[7]/a/@href")[0] + ".xml.gz")
            filenames.append(link.xpath("td[3]")[0].text.strip())
        return links, filenames
