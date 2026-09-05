from urllib.parse import urlsplit
import re
import ntpath
from abc import abstractmethod
from typing import AsyncGenerator
from lxml import html as lxml_html

from il_supermarket_scarper.utils import FileEntry


from il_supermarket_scarper.utils import (
    Logger,
    convert_nl_size_to_bytes,
    UnitSize,
    FilterState,
)
from il_supermarket_scarper.utils.async_work import stream_as_completed
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

    def _pages_to_scrape(self, main_page_request, total_pages):
        """Build the list of page request dicts for one listing root."""
        if total_pages is None:
            return [main_page_request]
        return [
            {
                **main_page_request,
                "url": (
                    main_page_request["url"]
                    + f"{self.page_argument}="
                    + str(page_number)
                ),
            }
            for page_number in range(1, total_pages + 1)
        ]

    async def _process_single_page(
        self,
        req,
        state,
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        random_selection=False,
    ):
        """Collect filtered FileEntry objects from one listing page."""
        results = []
        async for entry in self.process_links_before_download(
            state,
            req,
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            when_date=when_date,
            random_selection=random_selection,
        ):
            results.append(entry)
        return results

    async def _iter_page_requests(
        self, files_types=None, store_id=None, when_date=None
    ):
        """Yield page requests as each listing root's page count is known."""
        roots = self.get_request_url(
            files_types=files_types, store_id=store_id, when_date=when_date
        )

        async def resolve_root(main_page_request):
            main_page_response = await self.session_with_cookies_by_chain(
                **main_page_request
            )
            total_pages = self.get_number_of_pages(main_page_response)
            Logger.info(f"Found {total_pages} pages")
            return self._pages_to_scrape(main_page_request, total_pages)

        async for page_req in stream_as_completed(
            roots,
            resolve_root,
            max(1, self.max_threads),
            source_error_prefix="Error getting listing root URL",
            work_error_prefix="Error resolving listing root",
        ):
            yield page_req

    async def _stream_page_queue(
        self,
        page_source,
        state,
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        random_selection=False,
    ) -> AsyncGenerator[FileEntry, None]:
        """Yield page results with bounded in-flight fetches."""

        async def process_page(req):
            return await self._process_single_page(
                req,
                state,
                limit=limit,
                files_types=files_types,
                store_id=store_id,
                when_date=when_date,
                random_selection=random_selection,
            )

        async for entry in stream_as_completed(
            page_source,
            process_page,
            max(1, self.max_threads),
            source_error_prefix="Error reading listing page queue",
            work_error_prefix="Error fetching listing page",
        ):
            yield entry

    async def generate_all_files(
        self,
        files_types=None,
        store_id=None,
        when_date=None,
        limit=None,
        random_selection=False,
    ) -> AsyncGenerator[FileEntry, None]:
        """generate all files from the site"""

        pages = self._iter_page_requests(
            files_types=files_types, store_id=store_id, when_date=when_date
        )
        try:
            async for entry in self._stream_page_queue(
                pages,
                FilterState(),
                limit=limit,
                files_types=files_types,
                store_id=store_id,
                when_date=when_date,
                random_selection=random_selection,
            ):
                yield entry
        finally:
            await pages.aclose()

    async def collect_files_details_from_site(  # pylint: disable=too-many-locals
        self,
        state: FilterState,
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        file_name_regex=None,
        filter_null=False,
        filter_zero=False,
        min_size=None,
        max_size=None,
        random_selection=False,
    ) -> AsyncGenerator[tuple[str, str], None]:

        # Stream page results; close the root listing gen when limit/consumer
        # stops so unfinished page tasks are cancelled.
        listing = self.generate_all_files(
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            when_date=when_date,
            random_selection=random_selection,
        )
        try:
            files = self.register_all_saw_files_on_site(listing)

            # Filter by file size if specified
            if min_size is not None or max_size is not None:
                filtered_gen = self.filter_by_file_size(
                    files,
                    min_size=min_size,
                    max_size=max_size,
                )
            else:
                filtered_gen = files

            bad_files_filtered = self.filter_bad_files(
                filtered_gen,
                filter_null=filter_null,
                filter_zero=filter_zero,
                by_function=lambda x: x.name,
            )

            limited_files = self.apply_limit_zip(
                state,
                bad_files_filtered,
                limit=limit,
                files_types=files_types,
                by_function=lambda x: x.name,
                store_id=store_id,
                when_date=when_date,
                file_name_regex=file_name_regex,
                random_selection=random_selection,
            )

            async for entry in limited_files:
                yield entry.url, entry.name
        finally:
            await listing.aclose()

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
                yield FileEntry(name=name, url=url, size=size)

        # Apply filters but NOT the limit here to avoid race conditions when
        # processing pages in parallel. Limit is applied once in
        # collect_files_details_from_site as entries stream in.
        filtered_files = self.apply_limit_zip(
            state,
            generate_from_lists(),
            limit=None,  # Don't apply limit per page
            files_types=files_types,
            by_function=lambda x: x.name,
            store_id=store_id,
            when_date=when_date,
            random_selection=random_selection,
        )

        Logger.info(
            f"After applying filters: Page {request}: "
            f"Found {len(file_links)} files initially"
        )

        async for entry in filtered_files:
            yield entry
