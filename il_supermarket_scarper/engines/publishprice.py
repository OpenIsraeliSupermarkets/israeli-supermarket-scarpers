from bs4 import BeautifulSoup

from il_supermarket_scarper.utils import (
    Logger,
    session_and_check_status,
    _is_weekend_in_israel,
    _is_holiday_in_israel,
    _now,
)
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

        target_date = _now().strftime("%Y%m%d")
        current_date_page = list(
            filter(lambda x: target_date in str(x.a), soup.find_all("tr"))
        )
        assert len(current_date_page) == 1, f"can't find {target_date}"

        self.folder = current_date_page[0].a.attrs["href"]
        Logger.info(f"Looking at folder = {self.folder}")

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

    def get_store_name_format(self, store_id):
        return f"-{store_id:04d}-"

    def _is_validate_scraper_found_no_files(
        self, limit=None, files_types=None, store_id=None, only_latest=False
    ):
        return (
            super()._is_validate_scraper_found_no_files(  # what fails the rest
                limit=limit,
                files_types=files_types,
                store_id=store_id,
                only_latest=only_latest,
            )
            or (  # if we are looking for one store file in a weekend or holiday
                store_id and (_is_weekend_in_israel() or _is_holiday_in_israel())
            )
            or (  # if we are looking a specific number of file in a weekend or holiday
                limit is not None
                and (_is_weekend_in_israel() or _is_holiday_in_israel())
            )
        )
