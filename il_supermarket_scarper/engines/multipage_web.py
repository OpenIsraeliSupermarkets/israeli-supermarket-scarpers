from urllib.parse import urlsplit
import re
import ntpath
import lxml.html

from il_supermarket_scarper.utils.connection import download_connection_retry


from il_supermarket_scarper.utils import (
    Logger,
    execute_in_event_loop,
    multiple_page_aggregtion,
)
from .web import WebBase


class MultiPageWeb(WebBase):
    """scrape the file of websites with multipage"""

    target_file_extension = ".xml"
    results_in_page = 20

    def __init__(
        self,
        chain,
        chain_id,
        url="http://prices.shufersal.co.il/",
        folder_name=None,
        total_page_xpath="""//*[@id="gridContainer"]/table/
                                            tfoot/tr/td/a[6]/@href""",
        total_pages_pattern=r"^\/\?page\=([0-9]{2})$",
    ):
        super().__init__(chain, chain_id, url=url, folder_name=folder_name)
        self.total_page_xpath = total_page_xpath
        self.total_pages_pattern = total_pages_pattern

    @download_connection_retry()
    def get_number_of_pages(self, url):
        """get the number of pages to scarpe"""

        html = lxml.html.parse(url)

        total_pages = self.get_total_pages(html)
        Logger.info(f"Found {total_pages} pages")

        return total_pages

    def get_total_pages(self, html):
        """get the number of pages avaliabe to download"""

        elements = re.findall(
            self.total_pages_pattern,
            html.xpath(self.total_page_xpath)[-1],
        )
        if len(elements) != 1:
            raise ConnectionError(
                f"Didn't find the element contains number"
                f" of pages. found={elements}, in {html}."
            )
        return int(elements[0])

    def collect_files_details_from_site(self, limit=None, files_types=None):
        self.post_scraping()
        url = self.get_request_url()

        total_pages = self.get_number_of_pages(url[0])
        Logger.info(f"Found {total_pages} pages")

        pages_to_scrape = list(
            map(
                lambda page_number: self.url + "?page=" + str(page_number),
                range(1, total_pages + 1),
            )
        )

        download_urls, file_names = execute_in_event_loop(
            self.process_links_before_download,
            pages_to_scrape,
            aggregtion_function=multiple_page_aggregtion,
            max_workers=self.max_workers,
        )
        file_names, download_urls = self.apply_limit_zip(
            file_names, download_urls, limit=limit, files_types=files_types
        )

        return download_urls, file_names

    def collect_files_details_from_page(self, html):
        """collect the details deom one page"""
        links = []
        filenames = []
        for link in html.xpath('//*[@id="gridContainer"]/table/tbody/tr/td[1]/a/@href'):
            links.append(link)
            filenames.append(ntpath.basename(urlsplit(link).path).split(".")[0])
        return links, filenames

    def process_links_before_download(self, page, limit=None, files_types=None):
        """additional processing to the links before download"""
        response = self.session_with_cookies_by_chain(page)

        html = lxml.html.fromstring(response.text)

        file_links, filenames = self.collect_files_details_from_page(html)
        Logger.info(f"Page {page}: Found {len(file_links)} files")

        filenames, file_links = self.apply_limit_zip(
            filenames,
            file_links,
            limit=limit,
            files_types=files_types,
        )

        Logger.info(
            f"After applying limit: Page {page}: "
            f"Found {len(file_links)} line and {len(filenames)} files"
        )

        return file_links, filenames
