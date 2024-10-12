from bs4 import BeautifulSoup

from il_supermarket_scarper.utils import session_and_check_status
from .web import WebBase


class PublishPrice(WebBase):
    """
    scrape the file of PublishPrice
    possibly can support historical search: there is folder for each date.
    but this is not implemented.
    """

    def __init__(
        self,
        chain,
        chain_id,
        site_infix,
        folder_name=None,
        domain="prices",
        max_threads=5,
    ):
        super().__init__(
            chain,
            chain_id,
            url=f"https://{domain}.{site_infix}.co.il/",
            folder_name=folder_name,
            max_threads=max_threads,
        )
        self.folder = None

    def get_data_from_page(self, req_res):
        req_res = session_and_check_status(self.url)
        soup = BeautifulSoup(req_res.text, features="lxml")

        # the developer hard-coded the files names in the html
        all_trs = (
            soup.find_all("script")[-1]
            .text.replace("const files_html = [", "")
            .replace("];", "")
            .split("\n")[5]
            .split(",")
        )
        return list(map(lambda x: BeautifulSoup(x, features="lxml"), all_trs))

    def extract_task_from_entry(self, all_trs):
        """from the trs extract the download urls and file names"""

        def get_herf_element(x):
            return x.find_all("a")[-1]

        def get_herf(x):
            return get_herf_element(x).attrs["href"]

        def get_path_from_herf(x):
            return get_herf(x).replace("\\", "").replace('"', "").replace("./", "")

        def get_name_from_herf(x):
            return get_path_from_herf(x).split(".")[0].split("/")[-1]

        all_trs = list(
            filter(
                lambda x: get_herf_element(x) is not None,
                all_trs,
            )
        )

        download_urls: list = list(
            map(lambda x: self.url + get_path_from_herf(x), all_trs)
        )
        file_names: list = list(map(get_name_from_herf, all_trs))
        return download_urls, file_names

    # def _is_validate_scraper_found_no_files(
    #     self, limit=None, files_types=None, store_id=None, when_date=None
    # ):
    #     """return true if this is valid case where the scraper found no files"""
    #     return (
    #         super()._is_validate_scraper_found_no_files(  # what fails the rest
    #             limit=limit,
    #             files_types=files_types,
    #             store_id=store_id,
    #             when_date=when_date,
    #         )
    #         or (  # if we are looking for one store file in a weekend or holiday
    #             store_id and (_is_weekend_in_israel() or _is_holiday_in_israel())
    #         )
    #         or (  # if we are looking a specific number of file in a weekend or holiday
    #             limit is not None
    #             and (_is_weekend_in_israel() or _is_holiday_in_israel())
    #         )
    #     )
