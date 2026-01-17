import re
from bs4 import BeautifulSoup
from il_supermarket_scarper.utils import Logger
from il_supermarket_scarper.utils import convert_nl_size_to_bytes, UnitSize
from il_supermarket_scarper.utils.state import FilterState
from .engine import Engine


class WebBase(Engine):
    """scrape the file of websites that the only why to download them is via web"""

    def __init__(
        self,
        chain,
        chain_id,
        url,
        max_threads=5,
        file_output=None,
        status_database=None,
    ):
        super().__init__(
            chain,
            chain_id,
            max_threads=max_threads,
            file_output=file_output,
            status_database=status_database,
        )
        self.url = url
        self.max_retry = 2

    def get_data_from_page(self, req_res):
        """get the file list from a page"""
        soup = BeautifulSoup(req_res.text, features="lxml")
        return soup.find_all("tr")[1:]

    async def get_request_url(
        self, files_types=None, store_id=None, when_date=None
    ):  # pylint: disable=unused-argument
        """get all links to collect download links from"""
        yield {
            "url": self.url,
            "method": "GET",
        }

    def get_file_size_from_entry(self, entry):
        """
        Extract file size from a table row entry.
        Looks for size information in table cells, typically in human-readable format.
        Returns size in bytes, or None if not found.
        """
        try:
            size_match = re.search(r"\b\d+(\.\d+)?\s*(KB|MB|GB)\b", entry.text)
            if size_match is None:
                return None
            size_bytes = convert_nl_size_to_bytes(
                size_match.group(0), to_unit=UnitSize.BYTES
            )
            return size_bytes
        except (AttributeError, TypeError) as e:
            Logger.debug(f"Error extracting file size from entry: {e}")
        return None

    async def extract_task_from_entry(self, all_trs):
        """extract download links, file names, and file sizes from page list"""

        for x in all_trs:
            try:
                yield self.url + x.a.attrs["href"], x.a.attrs["href"].split(".")[
                    0
                ].split("/")[-1], self.get_file_size_from_entry(x)
            except (AttributeError, KeyError, IndexError, TypeError) as e:
                Logger.warning(f"Error extracting task from entry: {e}")

    async def apply_limit_zip(
        self,
        state: FilterState,
        files,
        limit=None,
        files_types=None,
        by_function=lambda x: x[0],
        store_id=None,
        when_date=None,
        files_names_to_scrape=None,
        random_selection=False,
    ):
        """apply limit to zip"""

        async for item in self.apply_limit(
            state,
            files,
            limit=limit,
            files_types=files_types,
            by_function=by_function,
            store_id=store_id,
            when_date=when_date,
            files_names_to_scrape=files_names_to_scrape,
            random_selection=random_selection,
        ):
            yield item

    async def generate_all_files(self, files_types=None, store_id=None, when_date=None):
        """Generate all files from the web site."""
        async for url in self.get_request_url(
            files_types=files_types, store_id=store_id, when_date=when_date
        ):
            req_res = await self.session_with_cookies_by_chain(**url)
            current_trs = self.get_data_from_page(req_res)
            async for file_entry in self.extract_task_from_entry(current_trs):
                yield file_entry

    async def collect_files_details_from_site( # pylint: disable=too-many-locals
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
    ):
        """collect all enteris to download from site"""
        # Generator to accumulate all extracted files from all pages
        extracted_files = self.generate_all_files(
            files_types=files_types, store_id=store_id, when_date=when_date
        )

        # Filter by file size if specified
        if min_size is not None or max_size is not None:
            filtered_files = self.filter_by_file_size(
                extracted_files,
                min_size=min_size,
                max_size=max_size,
            )
        else:
            filtered_files = extracted_files

        bad_files_filtered = self.filter_bad_files(
            filtered_files,
            filter_null=filter_null,
            filter_zero=filter_zero,
            by_function=lambda x: x[1],
        )

        async for download_url, file_name, _ in self.apply_limit(
            state,
            bad_files_filtered,
            limit=limit,
            files_types=files_types,
            by_function=lambda x: x[1],
            store_id=store_id,
            when_date=when_date,
            files_names_to_scrape=files_names_to_scrape,
            random_selection=random_selection,
        ):
            yield download_url, file_name

    async def process_file(self, file_details):
        """Process a single file from WebBase. file_details is (download_url, file_name) tuple."""
        download_url, file_name = file_details

        # Register that we've collected this file's details
        self.register_collected_file(
            file_name_collected_from_site=file_name,
            links_collected_from_site=download_url,
        )

        # Download and extract the file
        result = await self.save_and_extract((download_url, file_name))
        return result
