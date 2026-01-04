from datetime import timedelta
from bs4 import BeautifulSoup
from typing import Optional

from il_supermarket_scarper.utils import _now, Logger
from il_supermarket_scarper.engines.web import WebBase
from il_supermarket_scarper.engines.streaming import WebStreamingConfig, StorageType
from il_supermarket_scarper.utils import DumpFolderNames
from typing import List, Dict, Any, Optional


class Wolt(WebBase):
    """scraper for wolt with streaming support"""

    def __init__(self, streaming_config: Optional[WebStreamingConfig] = None):
        super().__init__(
            chain=DumpFolderNames.WOLT,
            chain_id="7290058249350",
            url="https://wm-gateway.wolt.com/isr-prices/public/v1/index.html",
            streaming_config=streaming_config
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
        """extract download links, file names, and file sizes from page list"""
        download_urls = []
        file_names = []
        file_sizes = []
        for x in all_trs:
            try:
                download_urls.append(x[1])
                file_names.append(x[0])
                file_sizes.append(None)
            except (AttributeError, KeyError, IndexError, TypeError) as e:
                Logger.warning(f"Error extracting task from entry: {e}")

        return download_urls, file_names, file_sizes
