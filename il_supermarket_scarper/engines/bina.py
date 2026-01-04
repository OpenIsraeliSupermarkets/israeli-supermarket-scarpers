import json
import urllib.parse
import datetime
from typing import Optional

from il_supermarket_scarper.utils import (
    Logger,
    url_connection_retry,
    url_retrieve,
    FileTypesFilters,
)
from typing import AsyncGenerator, Dict, Any
from .apsx import Aspx
from .streaming import WebStreamingConfig


class Bina(Aspx):
    """scraper for all Bina base site.
    Note! the websites have the possibility to download historical value as a date search menu.
    this class don't support downloading them.
    """

    def __init__(
        self,
        chain,
        chain_id,
        url_perfix,
        download_postfix="/Download.aspx?FileNm=",
        domain="binaprojects.com/",
        streaming_config: Optional[WebStreamingConfig] = None,
    ):
        super().__init__(
            chain,
            chain_id,
            url=f"http://{url_perfix}.{domain}",
            aspx_page="MainIO_Hok.aspx",
            streaming_config=streaming_config,
        )
        self.download_postfix = download_postfix

    async def file_type_ids(self, file_types) -> AsyncGenerator[int, None]:
        """get the file type id"""
        file_type_mapping = {
            FileTypesFilters.STORE_FILE.name: 1,
            FileTypesFilters.PRICE_FILE.name: 2,
            FileTypesFilters.PROMO_FILE.name: 3,
            FileTypesFilters.PRICE_FULL_FILE.name: 4,
            FileTypesFilters.PROMO_FULL_FILE.name: 5,
        }
        if file_types is None or file_types == FileTypesFilters.all_types():
            yield 0
        else:
            for file_type in file_types:
                if file_type not in file_type_mapping:
                    raise ValueError(f"File type {file_type} not supported")
                yield file_type_mapping[file_type]

    def _build_query_url(self, query_params, base_urls):
        
        for base in base_urls:
            yield {
                    "url": base + self.aspx_page + "?" + query_params,
                    "method": "GET",
                }

    async def _get_all_possible_query_string_params(
        self, files_types=None, store_id=None, when_date=None
    ):
        """get the arguments need to add to the url"""
        chains_urls = []

        for c_id in self.get_chain_id():
            chains_urls.append(
                {
                    "_": f"{c_id}",
                    "wReshet": "הכל",
                    "WFileType": "",
                    "WDate": "",
                    "WStore": "",
                }
            )

        # add file types to url
        if files_types:
            chains_urls_with_types = []
            async for files_type in self.file_type_ids(files_types):

                for chain_url in chains_urls:
                    chains_urls_with_types.append(
                        {**chain_url, "WFileType": files_type}
                    )
            chains_urls = chains_urls_with_types

        # add store id
        if store_id:
            for chains_url in chains_urls:
                chains_url["WStore"] = store_id

        # posting date
        if when_date and isinstance(when_date, datetime.datetime):
            for chains_url in chains_urls:
                chains_url["WDate"] = when_date.strftime("%d/%m/%Y")

        for chains_url in chains_urls:
            yield urllib.parse.urlencode(chains_url)

    def get_data_from_page(self, req_res):
        return json.loads(req_res.text)

    def get_href_from_entry(self, entry):
        """get download link for entry (tr)"""
        return self.download_postfix + entry["FileNm"]

    def get_file_name_no_ext_from_entry(self, entry):
        """get the file name without extensions from entey (tr)"""
        return entry.split(self.download_postfix)[-1].split(".")[0]

    def get_file_size_from_entry(self, entry):
        """
        Extract file size from a JSON entry.
        Bina returns JSON objects, check for size field.
        Returns size in bytes, or None if not found.
        """
        # Bina don't support file size in the entry
        return None

    @url_connection_retry()
    async def retrieve_file(self, file_link, file_save_path, timeout=30):
        response_content = await self.session_with_cookies_by_chain(
            file_link,
        )
        spath = json.loads(response_content.content)
        Logger.debug(f"Found spath: {spath}")

        url = spath[0]["SPath"]
        ext = file_link.split(".")[-1]

        url_retrieve(url, file_save_path + "." + ext, timeout=timeout)
        return file_save_path + "." + ext

    def _wget_file(self, file_link, file_save_path):
        response_content = self.session_with_cookies_by_chain(
            file_link,
        )
        spath = json.loads(response_content.content)
        Logger.debug(f"Found spath: {spath}")

        url = spath[0]["SPath"]
        ext = file_link.split(".")[-1]
        return super()._wget_file(url, file_save_path.split(".")[0] + "." + ext)
