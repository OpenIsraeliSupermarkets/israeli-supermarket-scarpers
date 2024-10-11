import json

from il_supermarket_scarper.utils import (
    Logger,
    url_connection_retry,
    session_and_check_status,
    url_retrieve,
    FileTypesFilters,
)

from .apsx import Aspx


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
        folder_name=None,
    ):
        super().__init__(
            chain,
            chain_id,
            url=f"http://{url_perfix}.{domain}",
            aspx_page="MainIO_Hok.aspx",
            folder_name=folder_name,
        )
        self.download_postfix = download_postfix

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

    def _build_query_url(self, query_params, base_urls):
        res = []
        for base in base_urls:
            res.append(
                {
                    "url": base + self.aspx_page + query_params,
                    "method": "GET",
                }
            )
        return res

    def _get_all_possible_query_string_params(
        self, files_types=None, store_id=None, when_date=None
    ):
        """get the arguments need to add to the url"""
        chains_urls = []
        if isinstance(self.chain_id, list):
            for c_id in self.chain_id:
                chains_urls.append(f"?_={c_id}")
        else:
            chains_urls.append(f"?_={self.chain_id}")

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
            for i in range(len(chains_urls)):
                chains_urls[i] = chains_urls[i] + f"&WStore={store_id}"

        # posting date
        if when_date:
            for i in range(len(chains_urls)):
                chains_urls[i] = chains_urls[i] + (
                    f"&WDate={when_date.strftime('%d/%m/%Y').reaplce('/','%2F')}"
                )
        return chains_urls

    def get_data_from_page(self, req_res):
        return json.loads(req_res.text)

    def get_href_from_entry(self, entry):
        """get download link for entry (tr)"""
        return self.download_postfix + entry["FileNm"]

    def get_file_name_no_ext_from_entry(self, entry):
        """get the file name without extensions from entey (tr)"""
        return entry.split(self.download_postfix)[-1].split(".")[0]

    @url_connection_retry()
    def retrieve_file(self, file_link, file_save_path, timeout=30):
        response_content = session_and_check_status(
            file_link,
        )

        spath = json.loads(response_content.content)
        Logger.info(f"Found spath: {spath}")

        url = spath[0]["SPath"]
        ext = file_link.split(".")[-1]

        url_retrieve(url, file_save_path + "." + ext, timeout=timeout)
        return file_save_path + "." + ext
