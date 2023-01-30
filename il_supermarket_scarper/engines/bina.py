import json

from il_supermarket_scarper.utils import (
    Logger,
    url_connection_retry,
    session_and_check_status,
    url_retrieve,
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
