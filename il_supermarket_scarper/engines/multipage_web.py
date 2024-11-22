from urllib.parse import urlsplit
import re
import ntpath
from abc import abstractmethod
from lxml import html as lxml_html


from il_supermarket_scarper.utils import (
    Logger,
    execute_in_parallel,
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
        url,
        folder_name=None,
        total_page_xpath="""//*[@id="gridContainer"]/table/
                                            tfoot/tr/td/a[6]/@href""",
        total_pages_pattern=r"^\/\?page\=([0-9]{3})$",
        page_argument="page",
        max_threads=5,
    ):
        super().__init__(
            chain, chain_id, url=url, folder_name=folder_name, max_threads=max_threads
        )
        self.total_page_xpath = total_page_xpath
        self.total_pages_pattern = total_pages_pattern
        self.page_argument = page_argument

    @abstractmethod
    def build_params(self, files_types=None, store_id=None, when_date=None):
        """build the params for the request"""

    def get_request_url(
        self, files_types=None, store_id=None, when_date=None
    ):  # pylint: disable=unused-argument
        """get all links to collect download links from"""

        results = []
        for arguments in self.build_params(
            files_types=files_types, store_id=store_id, when_date=when_date
        ):
            results.append(
                {
                    "url": self.url + arguments,
                    "method": "GET",
                }
            )
        return results

    def get_number_of_pages(self, response):
        """get the number of pages to scarpe"""

        html_body = lxml_html.fromstring(response.content)

        elements = html_body.xpath(self.total_page_xpath)

        if len(elements) == 0:
            return None  # only one page

        pages = re.findall(
            self.total_pages_pattern,
            elements[-1],
        )
        return int(pages[0])

    def collect_files_details_from_site(  # pylint: disable=too-many-locals
        self,
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        filter_null=False,
        filter_zero=False,
        files_names_to_scrape=None,
        suppress_exception=False,
    ):

        main_page_requests = self.get_request_url(
            files_types=files_types, store_id=store_id, when_date=when_date
        )
        assert len(main_page_requests) > 0, "No pages to scrape"

        download_urls = []
        file_names = []
        for main_page_request in main_page_requests:

            main_page_response = self.session_with_cookies_by_chain(**main_page_request)

            total_pages = self.get_number_of_pages(main_page_response)
            Logger.info(f"Found {total_pages} pages")

            # if there is only one page, call it again,
            # in the future, we can skip scrap it again
            if total_pages is None:
                pages_to_scrape = [main_page_request]
            else:
                pages_to_scrape = list(
                    map(
                        lambda page_number, req=main_page_request: {
                            **req,
                            "url": req["url"]
                            + f"{self.page_argument}="
                            + str(page_number),
                        },
                        range(1, total_pages + 1),
                    )
                )

            _download_urls, _file_names = execute_in_parallel(
                self.process_links_before_download,
                list(pages_to_scrape),
                aggregtion_function=multiple_page_aggregtion,
                max_threads=self.max_threads,
            )

            download_urls.extend(_download_urls)
            file_names.extend(_file_names)

        Logger.info(f"Found {len(download_urls)} files")

        file_names, download_urls = self.filter_bad_files_zip(
            file_names, download_urls, filter_null=filter_null, filter_zero=filter_zero
        )

        Logger.info(f"After filtering bad files: Found {len(download_urls)} files")

        file_names, download_urls = self.apply_limit_zip(
            file_names,
            download_urls,
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            when_date=when_date,
            files_names_to_scrape=files_names_to_scrape,
            suppress_exception=suppress_exception,
        )

        return download_urls, file_names

    def collect_files_details_from_page(self, html):
        """collect the details deom one page"""
        links = []
        filenames = []
        for link in html.xpath('//*[@id="gridContainer"]/table/tbody/tr/td[1]/a/@href'):
            links.append(link)
            filenames.append(ntpath.basename(urlsplit(link).path))
        return links, filenames

    def process_links_before_download(
        self,
        request,
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        suppress_exception=True,  # this is nested limit don't fail
    ):
        """additional processing to the links before download"""
        response = self.session_with_cookies_by_chain(**request)

        html = lxml_html.fromstring(response.text)

        file_links, filenames = self.collect_files_details_from_page(html)
        Logger.info(f"Page {request}: Found {len(file_links)} files")

        filenames, file_links = self.apply_limit_zip(
            filenames,
            file_links,
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            when_date=when_date,
            suppress_exception=suppress_exception,
        )

        Logger.info(
            f"After applying limit: Page {request}: "
            f"Found {len(file_links)} line and {len(filenames)} files"
        )

        return file_links, filenames
