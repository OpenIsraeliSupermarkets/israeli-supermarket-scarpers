from pathlib import Path
import re
import json
from il_supermarket_scarper.engines import MultiPageWeb
from il_supermarket_scarper.utils import Logger, download_connection_retry


class SuperPharm(MultiPageWeb):
    """scraper for super pharm"""

    def __init__(self, folder_name=None):
        super().__init__(
            chain="Super-Pharm",
            chain_id="7290172900007",
            url="http://prices.super-pharm.co.il/",
            folder_name=folder_name,
        )

    def get_total_pages(self, html):
        return int(
            re.findall(
                ".*?page\=([0-9]*)$", html.xpath('//*[@class="page_link"]//a/@href')[-1]
            )[0]
        )

    def collect_files_details_from_page(self, html):
        links = []
        filenames = []
        for element in html.xpath("//*/tr")[1:]:  # skip header
            links.append(self.url + element.xpath("./td[6]/a/@href")[0])
            filenames.append(element.xpath("./td[2]")[0].text.split(".")[0])
        return links, filenames

    @download_connection_retry()
    def retrieve_file(self, file_link, file_save_path):
        Logger.info(f"On a new Session: calling {file_link}")

        response_content = self.session_with_cookies_by_chain(file_link)
        spath = json.loads(response_content.content)
        Logger.info(f"Found spath: {spath}")

        file_to_save = self.session_with_cookies_by_chain(self.url + spath["href"])
        file_to_save_with_ext = file_save_path + ".gz"
        Path(file_to_save_with_ext).write_bytes(file_to_save.content)

        return file_to_save_with_ext
