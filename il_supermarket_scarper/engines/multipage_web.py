from urllib.parse import urlsplit
import re
import ntpath
from abc import abstractmethod
from lxml import html as lxml_html


from il_supermarket_scarper.utils import (
    Logger,
    execute_in_parallel,
    multiple_page_aggregtion,
    convert_nl_size_to_bytes,
    UnitSize,
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
        min_size=None,
        max_size=None,
    ):

        main_page_requests = self.get_request_url(
            files_types=files_types, store_id=store_id, when_date=when_date
        )
        assert len(main_page_requests) > 0, "No pages to scrape"

        download_urls = []
        file_names = []
        file_sizes = []
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

            _download_urls, _file_names, _file_sizes = execute_in_parallel(
                self.process_links_before_download,
                list(pages_to_scrape),
                aggregtion_function=multiple_page_aggregtion,
                max_threads=self.max_threads,
            )

            download_urls.extend(_download_urls)
            file_names.extend(_file_names)
            file_sizes.extend(
                _file_sizes if _file_sizes else [None] * len(_download_urls)
            )

        Logger.info(f"Found {len(download_urls)} files")

        # Filter by file size if specified
        if min_size is not None or max_size is not None:
            file_names, download_urls, file_sizes = self.filter_by_file_size(
                file_names,
                download_urls,
                file_sizes,
                min_size=min_size,
                max_size=max_size,
            )

        file_names, download_urls, file_sizes = self.filter_bad_files_zip(
            file_names,
            download_urls,
            file_sizes=file_sizes,
            filter_null=filter_null,
            filter_zero=filter_zero,
        )

        Logger.info(f"After filtering bad files: Found {len(download_urls)} files")

        file_names, download_urls, file_sizes = self.apply_limit_zip(
            file_names,
            download_urls,
            file_sizes=file_sizes,
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            when_date=when_date,
            files_names_to_scrape=files_names_to_scrape,
            suppress_exception=suppress_exception,
        )

        return download_urls, file_names

    def get_file_size_from_entry(self, html, link_element):  # pylint: disable=arguments-differ,unused-argument
        """
        Extract file size from HTML element.
        For MultiPageWeb, we need to find the size in the same row as the link.
        Returns size in bytes, or None if not found.
        """
        try:
            # Find the parent row of the link
            row = (
                link_element.getparent().getparent()
                if link_element.getparent()
                else None
            )
            if row is None:
                return None

            # Look for size in table cells - typically in a column after the link
            cells = row.xpath(".//td")
            for cell in cells:
                text = cell.text_content().strip() if cell.text_content() else ""
                # Parse size using the same logic as WebBase
                size_bytes = convert_nl_size_to_bytes(text, to_unit=UnitSize.BYTES)
                if size_bytes is not None:
                    return size_bytes
        except (AttributeError, TypeError) as e:
            Logger.debug(f"Error extracting file size from entry: {e}")
        return None

    def collect_files_details_from_page(self, html):
        """collect the details deom one page"""
        links = []
        filenames = []
        file_sizes = []
        link_elements = html.xpath('//*[@id="gridContainer"]/table/tbody/tr/td[1]/a')
        for link_element in link_elements:
            link = link_element.get("href")
            links.append(link)
            filenames.append(ntpath.basename(urlsplit(link).path))
            file_sizes.append(self.get_file_size_from_entry(html, link_element))
        return links, filenames, file_sizes

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

        file_links, filenames, file_sizes = self.collect_files_details_from_page(html)
        Logger.info(f"Page {request}: Found {len(file_links)} files")

        filenames, file_links, file_sizes = self.apply_limit_zip(
            filenames,
            file_links,
            file_sizes=file_sizes,
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

        return file_links, filenames, file_sizes
