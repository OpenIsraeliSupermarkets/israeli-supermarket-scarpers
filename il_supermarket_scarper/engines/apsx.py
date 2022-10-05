from abc import ABC, abstractmethod
from il_supermarket_scarper.utils import Logger

from .web import WebBase


class Aspx(WebBase, ABC):
    """class for aspx scapers"""

    def __init__(self, chain, chain_id, url, aspx_page, folder_name=None):
        super().__init__(chain, chain_id, url, folder_name=folder_name)
        self.aspx_page = aspx_page

    def extract_task_from_entry(self, all_trs):
        download_urls: list = list(
            map(lambda x: self.url + self.get_href_from_entry(x), all_trs)
        )
        file_names: list = list(
            map(self.get_file_name_no_ext_from_entry, download_urls)
        )
        return download_urls, file_names

    def _build_query_url(self, query_params):
        res = []
        for base in super().get_request_url():
            res.append(base + self.aspx_page + query_params)
        return res

    def _get_all_possible_query_string_params(self):
        """get the arguments need to add to the url"""
        if isinstance(self.chain_id, list):
            res = []
            for c_id in self.chain_id:
                res.append(f"?code=={c_id}")
            return res
        return [f"?code={self.chain_id}"]

    def get_request_url(self):
        result = []
        for query_params in self._get_all_possible_query_string_params():
            result.extend(self._build_query_url(query_params))
        Logger.info(f"Request url: {result}")
        return result

    @abstractmethod
    def get_href_from_entry(self, entry):
        """get download link for entry (tr)"""
        raise ValueError("abstract")

    @abstractmethod
    def get_file_name_no_ext_from_entry(self, entry):
        """get the file name without extensions from entey (tr)"""
        raise ValueError("abstract")
