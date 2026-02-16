from pathlib import Path
import urllib.parse
import datetime
from io import BytesIO

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
            total_page_xpath='//*[@class="mvc-grid-pager"]/button[last()]/@data-page',
            total_pages_pattern=r"(\d+)$",
            page_argument="&page",
        )

    def collect_files_details_from_page(self, html):
        links = []
        filenames = []
        file_sizes = []
        for element in html.xpath("//tbody/tr"):  # skip header
            links.append(self.url + element.xpath("./td[6]/a/@href")[0])
            filenames.append(element.xpath("./td[2]")[0].text)
            file_sizes.append(None)  # Super Pharm don't support file size in the entry
        return links, filenames, file_sizes

    @url_connection_retry()
    def retrieve_file_to_stream(self, file_link, timeout=15):
        Logger.debug(f"On a new Session: calling {file_link}")

        response_content = self.session_with_cookies_by_chain(
            file_link, timeout=timeout
        )
        spath = json.loads(response_content.content)
        Logger.debug(f"Found spath: {spath}")

        file_to_save = self.session_with_cookies_by_chain(
            self.url + spath["href"], timeout=timeout
        )
        buffer = BytesIO(file_to_save.content)
        buffer.seek(0)

        return buffer

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
            params = {}

            # The new website behavior is to filter base on the store name and not id
            # so we don't filter base on the store id in the request,
            #  only post collection filtering.
            # if store_id:
            #     params["store"] = store_id
            if when_date and isinstance(when_date, datetime.datetime):
                params["Date-equals"] = when_date.strftime("%d/%m/%Y")
            if files_types:
                params["Category-equals"] = ftype
            all_params.append(params)

        return ["?" + urllib.parse.urlencode(params) for params in all_params]
