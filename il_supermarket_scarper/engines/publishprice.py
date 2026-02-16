import json
from bs4 import BeautifulSoup

from il_supermarket_scarper.utils import FileEntry
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
        domain="prices",
        max_threads=5,
        file_output=None,
        status_database=None,
    ):
        super().__init__(
            chain,
            chain_id,
            url=f"https://{domain}.{site_infix}.co.il/",
            max_threads=max_threads,
            file_output=file_output,
            status_database=status_database,
        )
        self.folder = None

    async def get_request_url(
        self, files_types=None, store_id=None, when_date=None
    ):  # pylint: disable=unused-argument
        """get all links to collect download links from"""

        formated = ""
        if when_date:
            formated = when_date.strftime("%Y%m%d")
            formated = f"?p=./{formated}"
        yield {"url": self.url + formated, "method": "GET"}

    def get_data_from_page(self, req_res):
        soup = BeautifulSoup(req_res.text, features="lxml")

        # the developer hard-coded the files names in the html
        script_text = soup.find_all("script")[-2].text

        # Extract path (date folder)
        path_data = script_text.split("const path = ")[1]
        path = path_data.split(";")[0].strip().strip("'\"")

        # Extract files array
        all_data = script_text.split("const files = ")[1]
        all_files = json.loads(all_data.split("\n")[0].replace(";", ""))

        # Add path to each file entry and format size
        for file_entry in all_files:
            file_entry["path"] = path
            file_entry["size_formatted"] = file_entry.get("size", 0)

        # all_chains = json.loads(all_data.split("\n")[1])
        return all_files

    async def extract_task_from_entry(self, all_trs):
        """from the trs extract the download urls, file names, and file sizes"""

        for x in all_trs:
            try:
                # Format href with path: url/path/filename
                path = x.get("path", "")
                base_url = self.url.rstrip("/")
                if path:
                    href = f"{base_url}/{path}/{x['name']}"
                else:
                    href = f"{base_url}/{x['name']}"
                file_size = x.get("size_formatted", x.get("size", 0))
                yield FileEntry(name=x["name"], url=href, size=file_size)
            except (AttributeError, KeyError, IndexError, TypeError) as e:
                Logger.warning(f"Error extracting task from entry: {e}")
