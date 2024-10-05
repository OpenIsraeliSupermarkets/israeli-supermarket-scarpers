from abc import ABC, abstractmethod
from il_supermarket_scarper.utils import Logger, FileTypesFilters

from .web import WebBase


class Aspx(WebBase, ABC):
    """class for aspx scapers"""

    def __init__(
        self, chain, chain_id, url, aspx_page, folder_name=None, max_threads=5
    ):
        super().__init__(
            chain, chain_id, url, folder_name=folder_name, max_threads=max_threads
        )
        self.aspx_page = aspx_page

    def file_type_id(self, file_type):
        """get the file type id"""
        if file_type == FileTypesFilters.STORE_FILE.name:
            return 1
        if file_type == FileTypesFilters.PRICE_FILE.name:
            return 2
        if file_type == FileTypesFilters.PROMO_FILE.name:
            return 3
        if file_type == FileTypesFilters.PRICE_FULL_FILE.name:
            return 4
        if file_type == FileTypesFilters.PROMO_FULL_FILE.name:
            return 5
        raise ValueError(f"file type {file_type} not supported")

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

    def _get_all_possible_query_string_params(
        self, files_types=None, store_id=None, when_date=None
    ):
        """get the arguments need to add to the url"""
        if isinstance(self.chain_id, list):
            res = []
            for c_id in self.chain_id:
                res.append(f"?code={c_id}")
            return res
        chains_urls = [f"?code={self.chain_id}"]

        # add file types to url
        if files_types:
            chains_urls_with_types = []
            for files_type in files_types:
                file_type_id = self.file_type_id(files_type)
                chains_urls_with_types.extend(
                    [
                        f"{chain_url}&WFileType={file_type_id}"
                        for chain_url in chains_urls
                    ]
                )
            chains_urls = chains_urls_with_types

        # add store id
        if store_id:
            for chain_url in chains_urls:
                chain_url += f"&WStore={store_id}"

        # posting date
        if when_date:
            for chain_url in chains_urls:
                chain_url += (
                    f"&WDate={when_date.strftime('%d/%m/%Y').reaplce('/','%2F')}"
                )
        return chains_urls

    def get_request_url(self, files_types=None, store_id=None, when_date=None):
        result = []
        for query_params in self._get_all_possible_query_string_params(
            files_types=files_types, store_id=store_id, when_date=when_date
        ):
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
