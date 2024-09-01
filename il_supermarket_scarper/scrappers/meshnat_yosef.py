import json

from il_supermarket_scarper.engines.web import WebBase
from il_supermarket_scarper.engines import Bina

from il_supermarket_scarper.utils import _is_saturday_in_israel, _is_holiday_in_israel


class MeshnatYosef1(WebBase):
    """scraper for meshnat yoosef"""

    def __init__(self, folder_name=None):
        super().__init__(
            "Meshnat Yosef 1",
            chain_id="333333",
            url="https://list-files.w5871031-kt.workers.dev/",
            folder_name=folder_name,
        )

    def get_data_from_page(self, req_res):
        """get the file list from a page"""
        response = json.loads(req_res.text)
        return response

    def extract_task_from_entry(self, all_trs):
        """extract download links and file names from page list"""
        download_urls: list = list(map(lambda x: x["url"], all_trs))
        file_names: list = list(map(lambda x: x["name"], all_trs))

        return download_urls, file_names

    def _is_validate_scraper_found_no_files(
        self, limit=None, files_types=None, store_id=None, only_latest=False
    ):
        # no data on shabat
        return _is_saturday_in_israel() or _is_holiday_in_israel()


class MeshnatYosef2(Bina):
    """scaper for Meshnat Yosef"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain="MeshnatYosef2",
            chain_id="2222222",
            url_perfix="ktshivuk",
            folder_name=folder_name,
        )
