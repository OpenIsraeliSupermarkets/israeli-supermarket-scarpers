from bs4 import BeautifulSoup

from il_supermarket_scarper.utils.logger import Logger
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

    def get_request_url(
        self, files_types=None, store_id=None, when_date=None
    ):  # pylint: disable=unused-argument
        """get all links to collect download links from"""

        formated = ""
        if when_date:
            formated = when_date.strftime("%Y%m%d")
            formated = f"?p=./{formated}"
        return [{"url": self.url + formated, "method": "GET"}]

    def get_data_from_page(self, req_res):
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
            herfs = x.find_all("a")
            if len(herfs) > 0:
                return herfs[-1]
            return None

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

        download_urls = []
        file_names = []
        for x in all_trs:
            try:
                download_urls.append(self.url + get_path_from_herf(x))
                file_names.append(get_name_from_herf(x))
            except (AttributeError, KeyError, IndexError, TypeError) as e:
                Logger.warning(f"Error extracting task from entry: {e}")

        return download_urls, file_names
