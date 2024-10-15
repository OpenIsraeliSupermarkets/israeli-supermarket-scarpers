from pathlib import Path
import urllib.parse
import datetime

import json
from il_supermarket_scarper.engines import MultiPageWeb
from il_supermarket_scarper.utils import (
    Logger,
    url_connection_retry,
    DumpFolderNames,
    FileTypesFilters,
)


class SuperPharm(MultiPageWeb):
    """scraper for super pharm"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain=DumpFolderNames.SUPER_PHARM,
            chain_id="7290172900007",
            url="http://prices.super-pharm.co.il/",
            folder_name=folder_name,
            total_page_xpath='//*[@class="page_link"]//a/@href',
            total_pages_pattern=r".*?page\=([0-9]*)$",
            page_argument="&page",
        )

    def collect_files_details_from_page(self, html):
        links = []
        filenames = []
        for element in html.xpath("//*/tr")[1:]:  # skip header
            links.append(self.url + element.xpath("./td[6]/a/@href")[0])
            filenames.append(element.xpath("./td[2]")[0].text)
        return links, filenames

    @url_connection_retry()
    def retrieve_file(self, file_link, file_save_path, timeout=15):
        Logger.debug(f"On a new Session: calling {file_link}")

        response_content = self.session_with_cookies_by_chain(
            file_link, timeout=timeout
        )
        spath = json.loads(response_content.content)
        Logger.debug(f"Found spath: {spath}")

        file_to_save = self.session_with_cookies_by_chain(
            self.url + spath["href"], timeout=timeout
        )
        file_to_save_with_ext = file_save_path + ".gz"
        Path(file_to_save_with_ext).write_bytes(file_to_save.content)

        return file_to_save_with_ext

    def get_file_types_id(self, files_types=None):
        """get the file type id"""
        if files_types is None:
            return [""]

        types = []
        for ftype in files_types:
            if ftype == FileTypesFilters.STORE_FILE.name:
                types.append("StoresFull")
            if ftype == FileTypesFilters.PRICE_FILE.name:
                types.append("Price")
            if ftype == FileTypesFilters.PROMO_FILE.name:
                types.append("Promo")
            if ftype == FileTypesFilters.PRICE_FULL_FILE.name:
                types.append("PriceFull")
            if ftype == FileTypesFilters.PROMO_FULL_FILE.name:
                types.append("PromoFull")
        return types

    def build_params(self, files_types=None, store_id=None, when_date=None):
        """build the params for the request"""

        all_params = []
        for ftype in self.get_file_types_id(files_types):
            params = {"type": "", "date": "", "store": ""}

            if store_id:
                params["store"] = store_id
            if when_date and isinstance(when_date, datetime.datetime):
                params["date"] = when_date.strftime("%Y-%m-%d")
            if files_types:
                params["type"] = ftype
            all_params.append(params)

        return ["?" + urllib.parse.urlencode(params) for params in all_params]
