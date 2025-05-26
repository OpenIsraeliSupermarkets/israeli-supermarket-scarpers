from datetime import timedelta
from bs4 import BeautifulSoup

from il_supermarket_scarper.utils import _now, Logger
from il_supermarket_scarper.engines.web import WebBase

from il_supermarket_scarper.utils import DumpFolderNames


class Wolt(WebBase):
    """scraper for wolt"""

    def __init__(self, folder_name=None):
        super().__init__(
            DumpFolderNames.WOLT,
            chain_id="7290058249350",
            url="https://wm-gateway.wolt.com/isr-prices/public/v1/index.html",
            folder_name=folder_name,
        )

    def get_request_url(
        self, files_types=None, store_id=None, when_date=None
    ):  # pylint: disable=unused-argument
        """get all links to collect download links from"""
        if when_date:
            formatted_date = when_date.strftime("%Y-%m-%d")
            return [
                {
                    "url": self.url.replace("index.html", f"{formatted_date}.html"),
                    "method": "GET",
                }
            ]

        perspective = _now()
        all_pages_to_collect_from = []
        for days_back in range(10):
            formatted_date = (perspective - timedelta(days=days_back)).strftime(
                "%Y-%m-%d"
            )
            all_pages_to_collect_from.append(
                {
                    "url": self.url.replace("index.html", f"{formatted_date}.html"),
                    "method": "GET",
                }
            )
        return all_pages_to_collect_from

    def get_data_from_page(self, req_res):
        """get the file list from a page"""
        soup = BeautifulSoup(req_res.text, features="lxml")
        return list(
            map(
                lambda x: (x.text, self.url.replace("index.html", x.a.attrs["href"])),
                list(soup.find_all("li")),
            )
        )

    def extract_task_from_entry(self, all_trs):
        """extract download links and file names from page list"""
        download_urls = []
        file_names = []
        for x in all_trs:
            try:
                download_urls.append(x[1])
                file_names.append(x[0])
            except (AttributeError, KeyError, IndexError, TypeError) as e:
                Logger.warning(f"Error extracting task from entry: {e}")

        return download_urls, file_names
