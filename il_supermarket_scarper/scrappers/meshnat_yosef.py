import json

from il_supermarket_scarper.engines.web import WebBase
from il_supermarket_scarper.engines import Bina

from il_supermarket_scarper.utils import DumpFolderNames, Logger


class MeshnatYosef1(WebBase):
    """scraper for meshnat yoosef"""

    def __init__(self, folder_name=None):
        super().__init__(
            DumpFolderNames.MESHMAT_YOSEF_1,
            chain_id="5144744100002",
            url="https://list-files.w5871031-kt.workers.dev/",
            folder_name=folder_name,
        )

    def get_data_from_page(self, req_res):
        """get the file list from a page"""
        response = json.loads(req_res.text)
        return response

    def get_file_size_from_entry(self, entry):
        """
        Extract file size from a JSON entry.
        Returns size in bytes, or None if not found.
        """
        # Meshnat Yosef don't support file size in the entry
        return None

    def extract_task_from_entry(self, all_trs):
        """extract download links, file names, and file sizes from page list"""
        download_urls = []
        file_names = []
        file_sizes = []
        for x in all_trs:
            try:
                download_urls.append(x["url"])
                file_names.append(x["name"])
                file_sizes.append(self.get_file_size_from_entry(x))
            except (AttributeError, KeyError, IndexError, TypeError) as e:
                Logger.warning(f"Error extracting task from entry: {e}")

        return download_urls, file_names, file_sizes


class MeshnatYosef2(Bina):
    """scaper for Meshnat Yosef"""

    def __init__(self, folder_name=None):
        super().__init__(
            DumpFolderNames.MESHMAT_YOSEF_2,
            chain_id=["5144744100001", "7290058289400", "2222222"],
            url_perfix="ktshivuk",
            folder_name=folder_name,
        )
