from urllib.parse import urlsplit
import re
import ntpath
import asyncio
from abc import abstractmethod
from typing import AsyncGenerator

from lxml import html as lxml_html
from il_supermarket_scarper.utils import (
    Logger,
    convert_nl_size_to_bytes,
    UnitSize,
    FilterState,
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
        total_page_xpath="""//*[@id="gridContainer"]/table/
                                            tfoot/tr/td/a[6]/@href""",
        total_pages_pattern=r"^\/\?page\=([0-9]{3})$",
        page_argument="page",
        max_threads=5,
        file_output=None,
        status_database=None,
    ):
        super().__init__(
            chain,
            chain_id,
            url=url,
            max_threads=max_threads,
            file_output=file_output,
            status_database=status_database,
        )
        self.total_page_xpath = total_page_xpath
        self.total_pages_pattern = total_pages_pattern
        self.page_argument = page_argument

    @abstractmethod
    def build_params(self, files_types=None, store_id=None, when_date=None):
        """build the params for the request"""

    async def get_request_url(
        self, files_types=None, store_id=None, when_date=None
    ):  # pylint: disable=unused-argument
        """get all links to collect download links from"""

        for arguments in self.build_params(
            files_types=files_types, store_id=store_id, when_date=when_date
        ):
            yield {
                "url": self.url + arguments,
                "method": "GET",
            }

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
        if len(pages) != 1:
            raise ValueError(f"Found {len(pages)} pages, expected 1")

        return int(pages[0])

    async def generate_all_files(
        self,
        files_types=None,
        store_id=None,
        when_date=None,
        limit=None,
        random_selection=False,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """generate all files from the site"""

        async for main_page_request in self.get_request_url(
            files_types=files_types, store_id=store_id, when_date=when_date
        ):

            main_page_response = await self.session_with_cookies_by_chain(
                **main_page_request
            )

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

            # we pass the state between pages to keep the total input count
            # we don't pass the state to the process_links_before_download function
            # becuase later in the apply_limit function we will pass the state
            # to the apply_limit function
            cross_pages_state = FilterState()
            # Process pages in parallel using asyncio.gather

            async def process_single_page(req, state=cross_pages_state):
                results = []
                async for task in self.process_links_before_download(
                    state,
                    req,
                    limit=limit,
                    files_types=files_types,
                    store_id=store_id,
                    when_date=when_date,
                    random_selection=random_selection,
                ):
                    results.append(task)
                return results

            tasks = [process_single_page(req) for req in pages_to_scrape]
            for task_group in await asyncio.gather(*tasks):
                for task in task_group:
                    yield task

    async def collect_files_details_from_site(
        self,
        state: FilterState,
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        files_names_to_scrape=None,
        filter_null=False,
        filter_zero=False,
        min_size=None,
        max_size=None,
        random_selection=False,
    ) -> AsyncGenerator[tuple[str, str], None]:

        # Aggregate results from all pages
        files = self.generate_all_files(
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            when_date=when_date,
            random_selection=random_selection,
        )

        # Filter by file size if specified
        if min_size is not None or max_size is not None:
            filtered_gen = self.filter_by_file_size(
                files,
                min_size=min_size,
                max_size=max_size,
            )
        else:
            filtered_gen = files

        bad_files_filtered = self.filter_bad_files_zip(
            filtered_gen,
            filter_null=filter_null,
            filter_zero=filter_zero,
            by_function=lambda x: x[1],
        )

        limited_files = self.apply_limit_zip(
            state,
            bad_files_filtered,
            limit=limit,
            files_types=files_types,
            by_function=lambda x: x[1],
            store_id=store_id,
            when_date=when_date,
            files_names_to_scrape=files_names_to_scrape,
            random_selection=random_selection,
        )

        async for download_url, file_name, _ in limited_files:
            yield download_url, file_name

    def get_file_size_from_entry(
        self, html, link_element
    ):  # pylint: disable=arguments-differ,unused-argument
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
        # Select all rows from the table
        rows = html.xpath('//*[@id="gridContainer"]/table/tbody/tr')
        for row in rows:
            # Extract link from td[1]/a
            link_elements = row.xpath("./td[1]/a")
            if not link_elements:
                continue
            link_element = link_elements[0]
            link = link_element.get("href")
            if not link:
                continue

            # Extract size from td[3] (size column)
            size_elements = row.xpath("./td[3]")
            size_text = size_elements[0].text_content().strip() if size_elements else ""
            size_bytes = (
                convert_nl_size_to_bytes(size_text, to_unit=UnitSize.BYTES)
                if size_text
                else None
            )

            links.append(link)
            filenames.append(ntpath.basename(urlsplit(link).path))
            file_sizes.append(size_bytes)
        return links, filenames, file_sizes

    async def process_links_before_download(  # pylint: disable=too-many-locals
        self,
        state: FilterState,
        request,
        limit=None,  # pylint: disable=unused-argument
        files_types=None,
        store_id=None,
        when_date=None,
        random_selection=False,
    ):
        """additional processing to the links before download"""

        response = await self.session_with_cookies_by_chain(**request)

        html = lxml_html.fromstring(response.text)

        file_links, filenames, file_sizes = self.collect_files_details_from_page(html)
        Logger.info(f"Page {request}: Found {len(file_links)} files")

        # Create an async generator from the three lists
        async def generate_from_lists():
            for url, name, size in zip(file_links, filenames, file_sizes):
                yield url, name, size

        # Apply filters but NOT the limit here to avoid race conditions
        # when processing pages in parallel. The limit will be applied once
        # at the collect_files_details_from_site level after all pages are aggregated
        filtered_files = self.apply_limit_zip(
            state,
            generate_from_lists(),
            limit=None,  # Don't apply limit per page - let it be applied once after aggregation
            files_types=files_types,
            by_function=lambda x: x[1],
            store_id=store_id,
            when_date=when_date,
            random_selection=random_selection,
        )

        Logger.info(
            f"After applying filters: Page {request}: "
            f"Found {len(file_links)} files initially"
        )

        async for url, name, size in filtered_files:
            yield url, name, size
