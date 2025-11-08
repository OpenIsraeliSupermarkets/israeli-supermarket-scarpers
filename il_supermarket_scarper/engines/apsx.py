from abc import ABC, abstractmethod
from typing import Optional
from il_supermarket_scarper.utils import Logger

from .web import WebBase
from .streaming import WebStreamingConfig
from typing import AsyncGenerator, Dict, Any

class Aspx(WebBase, ABC):
    """class for aspx scapers"""

    def __init__(
        self, chain, chain_id, url, aspx_page,
        streaming_config: Optional[WebStreamingConfig] = None
    ):
        super().__init__(
            chain, chain_id, url,
            streaming_config=streaming_config
        )
        self.aspx_page = aspx_page

    async def extract_task_from_entry(self, all_trs) -> AsyncGenerator[Dict[str, Any], None]:
        """from the trs extract the download urls and file names"""

        for x in all_trs:
            try:
                download_url = self.url + self.get_href_from_entry(x)
                yield {
                    'download_url': download_url,
                    'file_name': self.get_file_name_no_ext_from_entry(download_url)
                }
            except (AttributeError, KeyError, IndexError, TypeError) as e:
                Logger.warning(f"Error extracting task from entry: {e}")
                yield None

    @abstractmethod
    async def _get_all_possible_query_string_params(
        self, files_types=None, store_id=None, when_date=None
    ):
        """list all param to add to the url"""

    @abstractmethod
    def _build_query_url(self, query_params, base_urls):
        """build the url with the query params"""

    async def get_request_url(self, files_types=None, store_id=None, when_date=None):
        """build the request given the base url and the query params"""
        async for query_params in self._get_all_possible_query_string_params(
            files_types=files_types, store_id=store_id, when_date=when_date
        ):
            yield self._build_query_url(query_params, [self.url])

    @abstractmethod
    def get_href_from_entry(self, entry):
        """get download link for entry (tr)"""

    @abstractmethod
    def get_file_name_no_ext_from_entry(self, entry):
        """get the file name without extensions from entey (tr)"""
