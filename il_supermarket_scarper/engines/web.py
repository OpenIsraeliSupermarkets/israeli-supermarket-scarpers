import re
import asyncio
from bs4 import BeautifulSoup
from il_supermarket_scarper.utils import Logger
from il_supermarket_scarper.utils import convert_nl_size_to_bytes, UnitSize
from il_supermarket_scarper.utils.state import FilterState
from .engine import Engine


class WebBase(Engine):
    """scrape the file of websites that the only why to download them is via web"""

    def __init__(self, chain, chain_id, url, folder_name=None, max_threads=5):
        super().__init__(chain, chain_id, folder_name, max_threads=max_threads)
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
            size_bytes = re.search(r"\b\d+(\.\d+)?\s*(KB|MB|GB)\b", entry.text)
            size_bytes = convert_nl_size_to_bytes(
                size_bytes.group(0), to_unit=UnitSize.BYTES
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
        suppress_exception=False,
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
            suppress_exception=suppress_exception,
            random_selection=random_selection,
        ):
            yield item

    async def filter_bad_files_zip(
        self,
        files,
        filter_null=False,
        filter_zero=False,
        by_function=lambda x: x[0],
    ):
        """apply bad files filtering to zip"""

        async for file in files:
            if self.is_pass_bad_files_filter(
                file, filter_zero, filter_null, by_function
            ):
                yield file

    async def generate_all_files(self, files_types=None, store_id=None, when_date=None):
        async for url in self.get_request_url(
            files_types=files_types, store_id=store_id, when_date=when_date
        ):
            req_res = await self.session_with_cookies_by_chain(**url)
            current_trs = self.get_data_from_page(req_res)
            async for file_entry in self.extract_task_from_entry(current_trs):
                yield file_entry
                
    async def collect_files_details_from_site(  # pylint: disable=too-many-locals
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
        random_selection=False,
    ):
        """collect all enteris to download from site"""
        state = FilterState()

        # Generator to accumulate all extracted files from all pages
        extracted_files = self.generate_all_files(files_types=files_types, store_id=store_id, when_date=when_date)

        # Filter by file size if specified
        if min_size is not None or max_size is not None:
            filtered_files = self.filter_by_file_size(
                extracted_files,
                min_size=min_size,
                max_size=max_size,
            )
        else:
            filtered_files = extracted_files

        bad_files_filtered = self.filter_bad_files_zip(
            filtered_files,
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
            suppress_exception=suppress_exception,
            random_selection=random_selection,
        )

        async for download_url, file_name, _ in limited_files:
            yield download_url, file_name

    async def _scrape(  # pylint: disable=too-many-locals
        self,
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        files_names_to_scrape=None,
        filter_null=False,
        filter_zero=False,
        suppress_exception=False,
        min_size=None,
        max_size=None,
        random_selection=False,
    ):
        """scarpe the files from multipage sites"""
        download_urls, file_names = [], []
        try:
            async for download_url, file_name in self.collect_files_details_from_site(
                limit=limit,
                files_types=files_types,
                store_id=store_id,
                when_date=when_date,
                filter_null=filter_null,
                filter_zero=filter_zero,
                files_names_to_scrape=files_names_to_scrape,
                suppress_exception=suppress_exception,
                min_size=min_size,
                max_size=max_size,
                random_selection=random_selection,
            ):
                download_urls.append(download_url)
                file_names.append(file_name)

            self.on_collected_details(file_names, download_urls)

            Logger.info(f"collected {len(download_urls)} to download.")
            if len(download_urls) > 0:
                tasks = [
                    self.save_and_extract((download_url, file_name))
                    for download_url, file_name in zip(download_urls, file_names)
                ]
                results = await asyncio.gather(*tasks)
            else:
                results = []

            for result in results:
                yield result
        except Exception as e:  # pylint: disable=broad-except
            self.on_download_fail(e, download_urls=download_urls, file_names=file_names)
            raise e
