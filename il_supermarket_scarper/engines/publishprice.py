from bs4 import BeautifulSoup

from il_supermarket_scarper.utils import Logger, session_and_check_status
from .web import WebBase


class PublishPrice(WebBase):
    """
    scrape the file of PublishPrice
    possibly can support historical search: there is folder for each date.
    but this is not implemented.
    """

    def __init__(self, chain, chain_id, site_infix, folder_name=None):
        super().__init__(
            chain,
            chain_id,
            url=f"http://publishprice.{site_infix}.co.il/",
            folder_name=folder_name,
        )
        self.folder = None

    def get_data_from_page(self, req_res):
        soup = BeautifulSoup(req_res.text, features="lxml")

        self.folder = soup.find_all("tr")[3].a.attrs["href"]
        Logger.info(f"Last folder is {self.folder}")

        req_res = session_and_check_status(self.url + self.folder)
        soup = BeautifulSoup(req_res.text, features="lxml")
        return soup.find_all("tr")[3:]

    def extract_task_from_entry(self, all_trs):
        # filter empty files
        all_trs = list(
            filter(
                lambda x: x.a is not None and x.contents[-1].string.strip() != "0",
                all_trs,
            )
        )

        download_urls: list = list(
            map(lambda x: self.url + self.folder + x.a.attrs["href"], all_trs)
        )
        file_names: list = list(map(lambda x: x.a.attrs["href"].split(".")[0], all_trs))
        return download_urls, file_names
