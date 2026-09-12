from abc import ABC, abstractmethod
from dataclasses import dataclass
from html import unescape
import os
import re
import shutil
import uuid
import datetime
import asyncio
from typing import AsyncGenerator, Optional
from il_supermarket_scarper.utils import (
    FileEntry,
    FileTypesFilters,
    Logger,
    ScraperStatus,
    session_with_cookies,
    url_retrieve_to_memory,
    wget_file_to_memory,
    RestartSessionError,
    DumpFolderNames,
    FileOutput,
    DiskFileOutput,
    ScrapingResult,
    async_url_connection_retry,
    content_sha256,
    SaveDecision,
)
from il_supermarket_scarper.utils.state import FilterState
from il_supermarket_scarper.utils.databases import AbstractDataBase
from il_supermarket_scarper.utils.async_work import stream_as_completed


@dataclass(frozen=True)
class LoginDetails:
    """Portal or FTP connection details for a scraper."""

    url: str
    username: Optional[str] = None
    password: Optional[str] = None


class Engine(ScraperStatus, ABC):  # pylint: disable=too-many-public-methods
    """
    Base engine class for scraping Israeli supermarket data.

    This abstract base class provides the core functionality for downloading
    and processing files from supermarket chains. Subclasses implement
    chain-specific logic for discovering and downloading files.

    The engine supports flexible output handling (disk or queue-based) and
    provides filtering capabilities for file types, sizes, and dates.

    Note:
        Output configuration priority: If ``file_output`` is provided, it is
        used directly. Otherwise, a ``DiskFileOutput`` is created using the
        chain's default storage path from ``DumpFolderNames``.

    Example:
        Basic usage with default disk output::

            from il_supermarket_scarper.scrappers_factory import ScraperFactory
            import asyncio

            scraper_class = ScraperFactory.get(ScraperFactory.WOLT)
            scraper = scraper_class()

            async def run():
                await scraper.scrape(limit=10)

            asyncio.run(run())

        With custom output directory::

            scraper = scraper_class(folder_name="custom_output")
            asyncio.run(scraper.scrape(limit=10))

        With queue output::

            from il_supermarket_scarper.utils import QueueFileOutput, InMemoryQueueHandler

            queue = InMemoryQueueHandler("test_queue")
            output = QueueFileOutput(queue)
            scraper = scraper_class(file_output=output)
            asyncio.run(scraper.scrape(limit=10))
    """

    _DATE_PATTERN_1 = re.compile(r"-(\d{8})(\d{4})?(?=-|\.|$)")
    _DATE_PATTERN_2 = re.compile(r"-(\d{8})-(\d{6})")

    utilize_date_param = True

    def __init__(
        self,
        chain,
        chain_id,
        max_threads=10,
        file_output: Optional[FileOutput] = None,
        status_database: Optional[AbstractDataBase] = None,
        listing_date_format=None,
        listing_date_key=None,
    ):
        """
        Initialize scraper engine.

        Args:
            chain (DumpFolderNames): Chain identifier enum value.
            chain_id (str): Unique identifier for the supermarket chain.
            max_threads (int, optional): Maximum number of concurrent download
                threads. Defaults to 10.
            file_output (FileOutput, optional): Custom file output handler.
                If None, a DiskFileOutput is created using the chain's default
                storage path. Defaults to None.
            status_database (AbstractDataBase, optional): Custom status database
                handler for tracking download status. If None, defaults to a
                status subdirectory in the file output path. Defaults to None.
            listing_date_format (str, optional): strptime format for listing
                published-at timestamps. Defaults to None.
            listing_date_key (str, optional): JSON/dict key for listing date
                fields (e.g. Bina DateFile). Defaults to None.

        Note:
            If file_output is provided, it takes precedence.
            Otherwise, a DiskFileOutput is created from the chain's default path.
            If status_database is not provided, defaults to a status subdirectory
            in the parent of file_output path.
        """
        assert DumpFolderNames.is_valid_folder_name(
            chain
        ), "chain name can contain only abc and -"

        self.chain = chain
        self.chain_id = chain_id
        self.max_threads = max_threads
        self.listing_date_format = listing_date_format
        self.listing_date_key = listing_date_key

        # Determine storage path
        if file_output is None:
            # Create storage path from folder_name and create DiskFileOutput
            file_output = DiskFileOutput(storage_path=DumpFolderNames[chain].value)

        super().__init__(
            chain.value, status_database=status_database, file_output=file_output
        )

        self.assigned_cookie = f"{self.chain.name}_{uuid.uuid4()}_cookies.txt"
        self.storage_path: FileOutput = file_output
        Logger.info(
            f"Initialized {self.chain.value} scraper with"
            f"output: {self.storage_path.get_output_location()}"
            f"status database: {status_database}"
            f"file output: {file_output}"
        )

    def get_storage_path(self):
        """
        Get the storage path where downloaded files are saved.

        Returns:
            str: The storage path string from the file output handler.
        """
        return self.storage_path.get_storage_path()

    def get_login_details(self) -> LoginDetails:
        """Return connection details: url, plus username/password when set."""
        url = getattr(self, "url", None)
        if not url:
            ftp_host = getattr(self, "ftp_host", None)
            if not ftp_host:
                raise AttributeError(f"{type(self).__name__} has no login details")
            ftp_path = getattr(self, "ftp_path", "") or ""
            url = f"ftp://{ftp_host}{ftp_path}"

        return LoginDetails(
            url=url,
            username=getattr(self, "ftp_username", None) or None,
            password=getattr(self, "ftp_password", None) or None,
        )

    def is_valid_file_empty(self, file_name):
        """
        Check if a file name represents an empty/valid file.

        Args:
            file_name (str): The file name to check.

        Returns:
            bool: True if the file name is None (considered valid/empty),
                False otherwise.
        """
        return file_name is None

    def is_pass_bad_files_filter(
        self,
        file: FileEntry,
        filter_zero=False,
        filter_null=False,
        by_function=lambda x: x.name,
    ):
        """
        Check if a file passes the bad files filter.

        Filters out files containing "0000000000000" (zero files) or "NULL"
        (null files) based on the provided flags.

        Args:
            file (tuple[str, str]): File tuple containing (link, name).
            filter_zero (bool, optional): If True, filter out zero files.
                Defaults to False.
            filter_null (bool, optional): If True, filter out NULL files.
                Defaults to False.
            by_function (callable, optional): Function to extract the string
                to check from the file tuple. Defaults to identity function.

        Returns:
            bool: True if file passes the filter, False if it should be filtered out.
        """
        if filter_zero and "0000000000000" in by_function(file):
            return False
        if filter_null and "NULL" in by_function(file):
            return False
        return True

    async def register_all_saw_files_on_site(
        self,
        files: AsyncGenerator[FileEntry, None],
    ) -> AsyncGenerator[FileEntry, None]:
        """register the file as saw on site"""
        async for file in files:
            self.register_saw_file(
                file_name=file.name,
                link=file.url,
                size=file.size,
            )
            yield file

    async def filter_bad_files(
        self,
        files: AsyncGenerator[FileEntry, None],
        filter_zero=False,
        filter_null=False,
        by_function=lambda x: x.name,
    ) -> AsyncGenerator[FileEntry, None]:
        """
        Filter out bad files from an async generator.

        Yields only files that pass the bad files filter.

        Args:
            files: Async generator yielding file tuples (link, name).
            filter_zero (bool, optional): Filter out zero files. Defaults to False.
            filter_null (bool, optional): Filter out NULL files. Defaults to False.
            by_function (callable, optional): Function to extract string from file tuple.
                Defaults to identity function.

        Yields:
            tuple[str, str]: File tuples that pass the filter.
        """
        async for file in files:
            if self.is_pass_bad_files_filter(
                file, filter_zero, filter_null, by_function
            ):
                yield file

    async def filter_by_store_id(
        self,
        intreable: AsyncGenerator[FileEntry, None],
        store_id=None,
        by_function=lambda x: x.name,
    ) -> AsyncGenerator[FileEntry, None]:
        """
        Filter files by store ID.

        Only yields files whose name contains the specified store ID.

        Args:
            intreable: Async generator yielding file tuples (link, name).
            store_id (str, optional): Store ID to filter by. If None, all files pass.
                Defaults to None.
            by_function (callable, optional): Function to extract string from file tuple.
                Defaults to identity function.

        Yields:
            tuple[str, str]: File tuples matching the store ID.
        """
        pattern = re.compile(rf"-0*{store_id}-")
        async for file in intreable:
            if pattern.search(by_function(file)):
                yield file

    async def filter_by_file_name_regex(
        self,
        intreable: AsyncGenerator[FileEntry, None],
        file_name_regex,
        by_function=lambda x: x.name,
    ):
        """Yield files whose name matches ``file_name_regex`` via ``re.search``."""
        pattern = self._compile_file_name_regex(file_name_regex)
        async for file in intreable:
            if pattern.search(by_function(file)):
                yield file

    async def apply_limit(
        self,
        state: FilterState,
        intreable: AsyncGenerator[FileEntry, None],
        limit=None,
        files_types=None,
        by_function=lambda x: x.name,
        store_id=None,
        when_date=None,
        file_name_regex=None,
        random_selection=False,
    ):
        """
        Apply filtering and limiting to a stream of files.

        This is a streaming version that processes files one at a time,
        applying various filters (already downloaded, identical listing
        hash, store ID, file name, file types, date) and enforcing the
        limit last so the quota is not spent on files later filters would
        drop. Duplicate FileNm values are kept when listing hash differs;
        FileOutput overwrites the disk file or re-queues under the same
        name. Identical listing hashes are dropped before download.

        Args:
            state (FilterState): State object tracking filter statistics.
            intreable: Async generator yielding file tuples (link, name).
            limit (int, optional): Maximum number of files to yield.
                If None, no limit is applied. Defaults to None.
            files_types (list, optional): File types to include.
                If None, all types are included. Defaults to None.
            by_function (callable, optional): Function to extract string from file tuple.
                Defaults to identity function.
            store_id (str, optional): Store ID to filter by. Defaults to None.
            when_date (datetime, optional): Date to filter files by.
                Defaults to None.
            file_name_regex (str, optional): Regex matched against file names
                with ``re.search``. Defaults to None (no name filter).
            random_selection (bool, optional): If True, randomly select files
                from the last 48 hours. Defaults to False.

        Yields:
            tuple[str, str]: Filtered file tuples.

        Note:
            If random_selection is enabled, only files from the last 48 hours
            are considered for selection.
        """

        # Stream one file at a time; date filters are online.
        async def stream_to_list(
            state: FilterState, intreable: AsyncGenerator[FileEntry, None]
        ) -> AsyncGenerator[FileEntry, None]:

            async for file in intreable:
                state.total_input += 1
                yield file

            if state.total_input == 0:
                Logger.warning(
                    f"No files to download for file files_types={files_types},"
                    f"limit={limit},store_id={store_id},when_date={when_date}"
                )
                return

        files_list = stream_to_list(state, intreable)

        # one download per listing identity in this scrape (not per FileNm)
        intreable_ = self.unique_listings(state, files_list)

        # filter files already downloaded
        intreable_: AsyncGenerator[FileEntry, None] = self.filter_already_downloaded(
            intreable_,
            by_function=by_function,
        )

        # filter by store id
        if store_id:
            intreable_ = self.filter_by_store_id(
                intreable_, store_id, by_function=by_function
            )

        if file_name_regex:
            intreable_ = self.filter_by_file_name_regex(
                intreable_, file_name_regex, by_function=by_function
            )

        # filter by file type (no limit — date and other filters still need to run)
        if files_types:
            intreable_ = self.filter_file_types(
                intreable_,
                files_types,
                by_function,
            )

        # Warning and filtering for random_selection
        if random_selection:
            Logger.warning(
                "random_selection is enabled. Will select only from files from the last 48 hours."
            )

        if isinstance(when_date, datetime.datetime):
            intreable_ = self.get_by_date(when_date, by_function, intreable_)
        elif when_date is not None:
            raise ValueError(
                f"when_date should be datetime or 'latest', got {when_date}"
            )

        if limit is not None:
            assert limit > 0, "Limit must be greater than 0"

        async for file in intreable_:
            if limit is not None and state.file_pass_limit >= limit:
                # Stop consuming; caller should aclose upstream listing gens
                # so parallel page/branch fetches can cancel.
                break
            state.file_pass_limit += 1
            yield file

        # raise error if there was nothing to download.
        if state.file_pass_limit == 0:
            Logger.warning(
                f"No files to download for file files_types={files_types},"
                f"limit={limit},store_id={store_id},when_date={when_date}"
            )

    @staticmethod
    async def unique_listings(state: FilterState, iterable):
        """Keep the first FileEntry per listing hash in this scrape.

        Same FileNm with a different url or size is a different listing and
        is kept. Identical listings are not downloaded twice.
        """
        async for item in iterable:
            listing_hash = item.listing_hash()
            if listing_hash not in state.unique_seen:
                state.unique_seen.add(listing_hash)
                yield item

    async def filter_file_types(
        self,
        intreable: AsyncGenerator[FileEntry, None],
        files_types,
        by_function,
    ) -> AsyncGenerator[FileEntry, None]:
        """Yield files matching the requested types. Does not apply limit."""

        async for type_ in intreable:
            filename = by_function(type_)
            if any(
                FileTypesFilters.is_file_from_type(filename, file_type)
                for file_type in files_types
            ):
                yield type_

    def get_only_latest(self, by_function, intreable_):
        """get only the last version of the files"""
        groups_max = {}
        groups_value = {}
        for file in intreable_:
            name_split = by_function(file).split("-")
            store_info = "-".join(name_split[:2])
            date_info = "-".join(name_split[2:]).rsplit(".", maxsplit=1)[-1]

            if store_info not in groups_max:
                groups_max[store_info] = date_info
                groups_value[store_info] = file
            elif groups_max[store_info] < date_info:
                groups_max[store_info] = date_info
                groups_value[store_info] = file
        return list(groups_value.values())

    async def get_by_date(self, requested_date, by_function, intreable_):
        """get by date"""
        date_format = requested_date.strftime("%Y%m%d")

        async for file in intreable_:
            # StoresFull7290875100001-000-202502250510'
            # Promo7290700100008-000-207-20250224-103225
            if f"-{date_format}" in by_function(file):
                yield file

    async def get_last_48_hours(self, by_function, intreable_):
        """get only files from the last 48 hours"""
        now = datetime.datetime.now()
        cutoff_time = now - datetime.timedelta(hours=48)

        groups_value = []
        for file in intreable_:
            file_name = by_function(file)
            # Extract date from filename patterns like:
            # StoresFull7290875100001-000-202502250510 (YYYYMMDDHHMM)
            # Promo7290700100008-000-207-20250224-103225 (YYYYMMDD-HHMMSS)
            # Look for date pattern YYYYMMDD followed by optional time
            # Pattern: -YYYYMMDD followed by optional HHMM, then - or end of string or .
            date_match = self._DATE_PATTERN_1.search(
                file_name
            ) or self._DATE_PATTERN_2.search(file_name)

            if not date_match:
                continue

            date_str = date_match.group(1)  # YYYYMMDD
            time_str = (date_match.group(2) or "0000")[:4]  # HHMM, default to 0000

            try:
                file_datetime = datetime.datetime.strptime(
                    f"{date_str}{time_str}", "%Y%m%d%H%M"
                )
                if file_datetime >= cutoff_time:
                    groups_value.append(file)

            except ValueError:
                continue

        return groups_value

    async def session_with_cookies_by_chain(
        self, url, method="GET", body=None, timeout=15, headers=None
    ):
        """request resource with cookie by chain name"""
        return await asyncio.to_thread(
            session_with_cookies,
            url,
            chain_cookie_name=self.assigned_cookie,
            timeout=timeout,
            method=method,
            body=body,
            headers=headers,
        )

    async def _post_scraping(self):
        """job to do post scraping"""
        if os.path.exists(self.assigned_cookie):
            os.remove(self.assigned_cookie)
        await self.storage_path.close()

    @staticmethod
    def _compile_file_name_regex(file_name_regex):
        """Compile ``file_name_regex`` or return None when unset."""
        if not file_name_regex:
            return None
        if not isinstance(file_name_regex, str):
            raise ValueError(
                "file_name_regex must be a string or None, "
                f"not {type(file_name_regex).__name__}"
            )
        try:
            return re.compile(file_name_regex)
        except re.error as exc:
            raise ValueError(
                f"file_name_regex is not a valid regular expression: {file_name_regex}"
            ) from exc

    def _validate_scraper_params(
        self, limit=None, files_types=None, store_id=None, file_name_regex=None
    ):
        if limit and limit <= 0:
            raise ValueError(f"limit must be greater than 0, nor {limit}")
        if files_types and files_types == []:
            raise ValueError(
                f"files_types must be a list of not empty file types or 'None', not {files_types}"
            )
        if store_id and store_id <= 0:
            raise ValueError(f"store_id must be greater than 1, not {store_id}")
        self._compile_file_name_regex(file_name_regex)

    async def scrape(  # pylint: disable=too-many-locals
        self,
        state: FilterState = None,
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
    ):
        """run the scraping logic"""
        self.on_scraping_start(
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            file_name_regex=file_name_regex,
            when_date=when_date,
            filter_null=filter_null,
            filter_zero=filter_zero,
        )
        self._validate_scraper_params(
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            file_name_regex=file_name_regex,
        )
        self.storage_path.make_sure_accassible()
        completed_successfully = True

        if state is None:
            state = FilterState()
        try:
            async for result in self._scrape(
                state,
                limit=limit,
                files_types=files_types,
                store_id=store_id,
                when_date=when_date,
                file_name_regex=file_name_regex,
                filter_null=filter_null,
                filter_zero=filter_zero,
                min_size=min_size,
                max_size=max_size,
                random_selection=random_selection,
            ):
                self.register_downloaded_file(result)
                yield result

        except Exception as e:  # pylint: disable=broad-exception-caught
            Logger.error(f"Error scraping: {e}")
            completed_successfully = False
        finally:
            self.on_scrape_completed(
                self.get_storage_path(), completed_successfully=completed_successfully
            )
            await self._post_scraping()

    @abstractmethod
    async def collect_files_details_from_site(
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
    ) -> AsyncGenerator:
        """Collect file details from the site.
        Should yield file details (format depends on subclass)."""

    @abstractmethod
    async def process_file(self, file_details) -> ScrapingResult:
        """
        Process a single file and return ScrapingResult.

        Args:
            file_details: File details from collect_files_details_from_site
                (format depends on subclass)

        Returns:
            ScrapingResult: Result of processing the file
        """

    def _extract_file_name(self, file_details):
        """Extract file name from file details for error reporting."""
        if isinstance(file_details, FileEntry):
            return file_details.name
        if isinstance(file_details, str):
            return file_details
        if isinstance(file_details, tuple) and len(file_details) > 1:
            return file_details[1]
        return "unknown"

    async def _scrape(  # pylint: disable=too-many-locals
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
    ) -> AsyncGenerator[ScrapingResult, None]:
        """scrape the files with concurrent streaming downloads"""

        # Semaphore to limit concurrent downloads
        semaphore = asyncio.Semaphore(self.max_threads)

        # Helper function to process a single file with semaphore
        async def process_file_with_semaphore(file_details):
            async with semaphore:
                try:
                    return await self.process_file(file_details)
                except Exception as e:  # pylint: disable=broad-except
                    Logger.error(f"Error in process_file: {e}")
                    file_name = self._extract_file_name(file_details)
                    self.register_download_fail(e, file_name)
                    return ScrapingResult(
                        file_entry=file_details,
                        downloaded=False,
                        save_decision=None,
                        extract_succefully=False,
                        error=str(e),
                        restart_and_retry=False,
                    )

        files_generator = self.collect_files_details_from_site(
            state,
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            when_date=when_date,
            filter_null=filter_null,
            filter_zero=filter_zero,
            file_name_regex=file_name_regex,
            min_size=min_size,
            max_size=max_size,
            random_selection=random_selection,
        )

        async for result in stream_as_completed(
            files_generator,
            process_file_with_semaphore,
            self.max_threads,
            source_error_prefix="Error collecting file details",
            work_error_prefix="Error processing download",
        ):
            yield result

    def get_chain_id(self):
        """get the chain id as list"""
        if isinstance(self.chain_id, list):
            return self.chain_id
        return [self.chain_id]

    def get_chain_name(self):
        """return chain name"""
        return self.chain

    def get_file_size_from_entry(self, entry):  # pylint: disable=unused-argument
        """
        Extract file size from an entry (table row).
        Returns file size in bytes, or None if size information is not available.
        Default implementation returns None - should be overridden by subclasses.
        """
        return None

    def is_pass_file_size_filter(self, file_size, min_size=None, max_size=None):
        """check if the file size is within the range"""
        if min_size is None and max_size is None:
            return True
        # If file_size is None, we can't filter it, so keep it
        if file_size is None:
            return True
        if min_size is not None and file_size < min_size:
            return False
        if max_size is not None and file_size > max_size:
            return False
        return True

    async def filter_by_file_size(
        self,
        files: AsyncGenerator[FileEntry, None],
        min_size=None,
        max_size=None,
    ) -> AsyncGenerator[FileEntry, None]:
        """
        Filter files by size (in bytes).
        Yields filtered FileEntry instances.
        Entries with None file_size are kept by default.
        """
        async for entry in files:
            if self.is_pass_file_size_filter(entry.size, min_size, max_size):
                yield entry

    @async_url_connection_retry()
    async def retrieve_file_to_memory(self, file_link, timeout=30):
        """download file directly to memory"""
        return await asyncio.to_thread(
            url_retrieve_to_memory, file_link, timeout=timeout
        )

    async def _wget_file_to_memory(self, file_link, timeout):
        return await wget_file_to_memory(file_link, timeout)

    async def _download_file_content(self, file_link, timeout=30):
        """Download file bytes; fall back to wget if requests fails."""
        file_link = unescape(file_link)
        try:
            return await self.retrieve_file_to_memory(file_link, timeout=timeout)
        except Exception as e:  # pylint: disable=broad-except
            Logger.warning(f"Error downloading {file_link}: {e}")
            if not shutil.which("wget"):
                raise
            return await self._wget_file_to_memory(file_link, timeout)

    async def save_and_extract(  # pylint: disable=too-many-locals
        self, entry: FileEntry
    ):
        """download file and extract it (in-memory)

        Re-downloads a few times on extract failure. If extract still fails
        after full downloads, mark ``source_corrupt`` (remote file is bad).
        """

        file_link, file_name = entry.url, entry.name
        Logger.debug(f"Processing {file_link} (in-memory)")

        downloaded = False
        error = None
        restart_and_retry = False
        source_corrupt = False
        max_attempts = 3
        result = None
        saved_file_name = None

        try:
            # Determine file name with extension (case-insensitive check)
            file_name_with_ext = file_name
            file_link_lower = file_link.lower()
            file_name_lower = file_name.lower()
            if file_link_lower.endswith(
                (".gz", ".xml")
            ) and not file_name_lower.endswith((".gz", ".xml")):
                file_name_with_ext = file_name + "." + file_link.split(".")[-1].lower()

            file_link = unescape(file_link)
            for attempt in range(1, max_attempts + 1):
                file_content = await self._download_file_content(file_link, timeout=30)
                downloaded = True

                if file_name_with_ext.endswith(".gz"):
                    Logger.debug(f"File size is {len(file_content)} bytes.")

                (
                    file_content,
                    extracted_name,
                    extract_ok,
                    extract_error,
                ) = await self.storage_path.extract_if_compressed(
                    file_content,
                    file_name_with_ext,
                    getattr(self.storage_path, "extract_gz", True),
                )
                error = extract_error
                if not extract_ok:
                    Logger.warning(
                        f"Extract failed for {file_name} "
                        f"(attempt {attempt}/{max_attempts}): {error}"
                    )
                    if attempt == max_attempts:
                        source_corrupt = True
                        error = (
                            f"source corrupt after {max_attempts} downloads: "
                            f"{error or 'extract failed'}"
                        )
                        Logger.error(error)
                    continue

                digest = content_sha256(file_content)
                metadata = {
                    "chain": self.chain.value,
                    "chain_id": self.chain_id,
                    "original_filename": file_name,
                    "published_at": entry.published_at,
                }
                box = {"result": None}

                async def _persist(
                    content=file_content,
                    name=extracted_name,
                    meta=metadata,
                    dig=digest,
                ):
                    box["result"] = await self.storage_path.save_file(
                        file_link=file_link,
                        file_name=name,
                        file_content=content,
                        metadata=meta,
                        save_decision=SaveDecision.CREATED,
                        content_digest=dig,
                    )

                save_decision = await self.decide_and_persist(
                    extracted_name,
                    digest,
                    entry.published_at,
                    _persist,
                    listing_hash=entry.listing_hash(),
                )
                if box["result"] is not None:
                    result = box["result"]
                    result["save_decision"] = save_decision
                else:
                    result = {
                        "file_name": extracted_name,
                        "saved": True,
                        "extract_successfully": True,
                        "error": None,
                        "content_sha256": digest,
                        "save_decision": save_decision,
                        "metadata": metadata,
                    }

                saved_file_name = extracted_name
                return ScrapingResult(
                    file_entry=entry,
                    downloaded=downloaded,
                    save_decision=result["save_decision"],
                    extract_succefully=True,
                    content_sha256=result["content_sha256"],
                    error=None,
                    restart_and_retry=False,
                    source_corrupt=False,
                    saved_file_name=saved_file_name,
                )

            return ScrapingResult(
                file_entry=entry,
                downloaded=downloaded,
                save_decision=None if result is None else result["save_decision"],
                extract_succefully=False,
                content_sha256=None if result is None else result["content_sha256"],
                error=error,
                restart_and_retry=False,
                source_corrupt=source_corrupt,
                saved_file_name=saved_file_name,
            )

        except RestartSessionError as exception:
            Logger.error(f"Error processing {file_link}, downloaded={downloaded}")
            Logger.error_execption(exception)
            error = str(exception)
            restart_and_retry = True
        except Exception as exception:  # pylint: disable=broad-except
            Logger.error(f"Error processing {file_link}, downloaded={downloaded}")
            Logger.error_execption(exception)
            error = str(exception)

        return ScrapingResult(
            file_entry=entry,
            downloaded=downloaded,
            save_decision=None if result is None else result["save_decision"],
            extract_succefully=False,
            content_sha256=None if result is None else result["content_sha256"],
            error=error,
            restart_and_retry=restart_and_retry,
            source_corrupt=source_corrupt,
            saved_file_name=saved_file_name,
        )

