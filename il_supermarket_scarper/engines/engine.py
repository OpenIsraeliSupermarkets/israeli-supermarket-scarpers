from abc import ABC, abstractmethod
import os
import re
import uuid
import datetime
import asyncio
from typing import AsyncGenerator, Optional
from il_supermarket_scarper.utils import (
    get_output_folder,
    FileTypesFilters,
    Logger,
    ScraperStatus,
    extract_xml_file_from_gz_file,
    session_with_cookies,
    url_retrieve,
    wget_file,
    RestartSessionError,
    DumpFolderNames,
    FileOutput,
    DiskFileOutput,
)
from il_supermarket_scarper.utils.state import FilterState


class Engine(ScraperStatus, ABC):  # pylint: disable=too-many-public-methods
    """base engine for scraping"""

    utilize_date_param = True

    def __init__(
        self,
        chain,
        chain_id,
        max_threads=10,
        file_output: Optional[FileOutput] = None,
    ):
        """
        Initialize scraper engine.

        Args:
            chain: Chain identifier (DumpFolderNames enum)
            chain_id: Chain ID
            folder_name: Output folder name (used if file_output not provided)
            max_threads: Maximum concurrent threads
            file_output: Optional custom file output handler

        Note:
            If file_output is provided, it takes precedence over folder_name.
            Otherwise, a DiskFileOutput is created from folder_name.
        """
        assert DumpFolderNames.is_valid_folder_name(
            chain
        ), "chain name can contain only abc and -"

        self.chain = chain
        self.chain_id = chain_id
        self.max_threads = max_threads

        # Determine storage path
        if file_output is None:
            # Create storage path from folder_name and create DiskFileOutput
            file_output = DiskFileOutput(storage_path=DumpFolderNames[chain].value)

        # Initialize status tracking (uses folder for status DB location)
        super().__init__(chain.value, "status", file_output=file_output)

        self.assigned_cookie = f"{self.chain.name}_{uuid.uuid4()}_cookies.txt"
        self.storage_path = file_output
        Logger.info(
            f"Initialized {self.chain.value} scraper with output: {self.storage_path}"
        )

    def get_storage_path(self):
        """the the storage page of the files downloaded"""
        return self.storage_path.get_storage_path()

    def is_valid_file_empty(self, file_name):
        """it is valid the file is empty"""
        return file_name is None

    def is_pass_bad_files_filter(
        self,
        file: tuple[str, str],
        filter_zero=False,
        filter_null=False,
        by_function=lambda x: x,
    ):
        """check if the file is pass the bad files filter"""
        if filter_zero and "0000000000000" in by_function(file):
            return False
        if filter_null and "NULL" in by_function(file):
            return False
        return True

    async def filter_bad_files(
        self,
        files: AsyncGenerator[tuple[str, str], None],
        filter_zero=False,
        filter_null=False,
        by_function=lambda x: x,
    ):
        """filter out bad files"""

        async for file in files:
            if not self.is_pass_bad_files_filter(
                file, filter_zero, filter_null, by_function
            ):
                continue
            yield file

    async def filter_by_store_id(
        self,
        state: FilterState,  # pylint: disable=unused-argument
        intreable: AsyncGenerator[tuple[str, str], None],
        store_id=None,
        by_function=lambda x: x,
    ):
        """filter the files by the store id"""
        pattern = re.compile(rf"-0*{store_id}-")
        async for file in intreable:
            if pattern.search(by_function(file)):
                yield file

    async def apply_limit(
        self,
        state: FilterState,
        intreable: AsyncGenerator[tuple[str, str], None],
        limit=None,
        files_types=None,
        by_function=lambda x: x,
        store_id=None,
        when_date=None,
        files_names_to_scrape=None,
        suppress_exception=False,
        random_selection=False,
    ):
        """filter the list according to condition - streaming version that
        processes each file at a time"""

        # Collect all input files first (needed for unique, latest,
        # random_selection)
        async def stream_to_list(
            state: FilterState, intreable: AsyncGenerator[tuple[str, str], None]
        ):

            async for file in intreable:
                state.total_input += 1
                yield file

            if state.total_input == 0:
                if not suppress_exception:
                    raise ValueError(
                        f"No files to download for file files_types={files_types},"
                        f"limit={limit},store_id={store_id},when_date={when_date}"
                    )
                Logger.warning(
                    f"No files to download for file files_types={files_types},"
                    f"limit={limit},store_id={store_id},when_date={when_date}"
                )
                return

        files_list = stream_to_list(state, intreable)

        # filter files already downloaded
        intreable_: AsyncGenerator[tuple[str, str], None] = (
            self.filter_already_downloaded(
                self.storage_path.get_storage_path(),
                files_names_to_scrape,
                files_list,
                by_function=by_function,
            )
        )

        Logger.info(
            f"Number of entry after filter already downloaded is {state.after_already_downloaded}"
        )

        # filter unique links
        intreable_ = self.unique(state, intreable_, by_function=by_function)
        Logger.info(
            f"Number of entry after filter unique links is {state.after_unique}"
        )

        # filter by store id
        if store_id:
            intreable_ = self.filter_by_store_id(
                state, intreable_, store_id, by_function=by_function
            )

        Logger.info(f"Number of entry after filter store id is {state.after_store_id}")

        # filter by file type
        if files_types:
            intreable_ = self.filter_file_types(
                state,
                intreable_,
                limit,
                files_types,
                by_function,
                random_selection=random_selection,
            )

        Logger.info(
            f"Number of entry after filter file type id is {state.after_file_types}"
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

        # Yield files, applying limit if files_types filter is not on
        if limit and not files_types:
            assert limit > 0, "Limit must be greater than 0"
            async for file in intreable_:
                if state.file_pass_limit < limit:
                    state.file_pass_limit += 1
                    yield file
        else:
            # When files_types is set, filter_file_types already applied the limit
            # Just yield all filtered files
            async for file in intreable_:
                yield file

        # raise error if there was nothing to download.
        if state.file_pass_limit == 0:
            if not suppress_exception:
                raise ValueError(
                    f"No files to download for file files_types={files_types},"
                    f"limit={limit},store_id={store_id},when_date={when_date}"
                )
            Logger.warning(
                f"No files to download for file files_types={files_types},"
                f"limit={limit},store_id={store_id},when_date={when_date}"
            )

    async def filter_file_types(
        self,
        state: FilterState,
        intreable,
        limit,
        files_types,
        by_function,
        random_selection=False,  # pylint: disable=unused-argument
    ):
        """filter the file types requested"""

        async for type_ in intreable:
            # Check if the file matches any of the requested file types
            filename = by_function(type_)
            matches = any(
                FileTypesFilters.is_file_from_type(filename, file_type)
                for file_type in files_types
            )
            if matches and state.file_pass_limit < limit:
                state.file_pass_limit += 1
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
        #
        date_format = requested_date.strftime("%Y%m%d")
        #
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
            date_match = re.search(r"-(\d{8})(\d{4})?(?=-|\.|$)", file_name)
            if not date_match:
                # Try pattern with date and time separated by dash: -YYYYMMDD-HHMMSS
                date_match = re.search(r"-(\d{8})-(\d{6})", file_name)
                if date_match:
                    date_str = date_match.group(1)  # YYYYMMDD
                    time_str = date_match.group(2)[
                        :4
                    ]  # Take first 4 digits (HHMM) from HHMMSS
                    try:
                        file_datetime = datetime.datetime.strptime(
                            f"{date_str}{time_str}", "%Y%m%d%H%M"
                        )
                        if file_datetime >= cutoff_time:
                            groups_value.append(file)
                    except ValueError:
                        continue
            else:
                date_str = date_match.group(1)  # YYYYMMDD
                time_str = (
                    date_match.group(2) if date_match.group(2) else "0000"
                )  # HHMM or default to 0000
                try:
                    file_datetime = datetime.datetime.strptime(
                        f"{date_str}{time_str}", "%Y%m%d%H%M"
                    )
                    if file_datetime >= cutoff_time:
                        groups_value.append(file)
                except ValueError:
                    # If parsing fails, skip this file
                    continue

        return groups_value

    @classmethod
    async def unique(cls, state: FilterState, iterable, by_function=lambda x: x):
        """Returns the type of the file."""
        async for item in iterable:
            k = by_function(item)
            if k not in state.unique_seen:
                state.unique_seen.add(k)
                yield item

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

    def _post_scraping(self):
        """job to do post scraping"""
        if os.path.exists(self.assigned_cookie):
            os.remove(self.assigned_cookie)

    def _validate_scraper_params(self, limit=None, files_types=None, store_id=None):
        if limit and limit <= 0:
            raise ValueError(f"limit must be greater than 0, nor {limit}")
        if files_types and files_types == []:
            raise ValueError(
                f"files_types must be a list of not empty file types or 'None', not {files_types}"
            )
        if store_id and store_id <= 0:
            raise ValueError(f"store_id must be greater than 1, not {store_id}")

    async def scrape(  # pylint: disable=too-many-locals
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
        """run the scraping logic"""
        self.on_scraping_start(
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            files_names_to_scrape=files_names_to_scrape,
            when_date=when_date,
            filter_nul=filter_null,
            filter_zero=filter_zero,
            suppress_exception=suppress_exception,
        )
        self._validate_scraper_params(
            limit=limit, files_types=files_types, store_id=store_id
        )
        self.storage_path.make_sure_accassible()
        completed_successfully = True
        results = []
        try:
            async for result in self._scrape(
                limit=limit,
                files_types=files_types,
                store_id=store_id,
                when_date=when_date,
                files_names_to_scrape=files_names_to_scrape,
                filter_null=filter_null,
                filter_zero=filter_zero,
                suppress_exception=suppress_exception,
                min_size=min_size,
                max_size=max_size,
                random_selection=random_selection,
            ):
                results.append(result)
            self.on_download_completed(results=results)
        except Exception as e:  # pylint: disable=broad-exception-caught
            if not suppress_exception:
                raise e
            Logger.warning(f"Suppressing exception! {e}")
            completed_successfully = False
        finally:
            self.on_scrape_completed(
                self.get_storage_path(), completed_successfully=completed_successfully
            )
            self._post_scraping()

        return results

    @abstractmethod
    async def _scrape(
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
        """method to be implemeted by the child class"""

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
        files: AsyncGenerator[tuple[str, str, int], None],
        min_size=None,
        max_size=None,
    ):
        """
        Filter files by size (in bytes).
        Yields filtered (file_name, download_url, file_size) tuples.
        Entries with None file_size are kept by default.
        """
        if min_size is None and max_size is None:
            # No filtering needed, yield all items
            async for name, url, size in files:
                yield name, url, size
        else:

            async for name, url, size in files:
                # Keep entries with None size (can't filter them)
                if self.is_pass_file_size_filter(size, min_size, max_size):
                    yield name, url, size

    async def retrieve_file(self, file_link, file_save_path, timeout=30):
        """download file"""
        await asyncio.to_thread(
            url_retrieve, file_link, file_save_path, timeout=timeout
        )
        return file_save_path

    async def save_and_extract(self, arg):
        """download file and extract it"""

        file_link, file_name = arg
        Logger.debug(f"Processing {file_link}")

        # Download the file content first
        downloaded = False
        error = None
        restart_and_retry = False

        try:
            # Determine file path for temporary download
            file_save_path = os.path.join(
                self.storage_path.get_storage_path(), file_name
            )

            # Add extension if needed
            if not (
                file_save_path.endswith(".gz") or file_save_path.endswith(".xml")
            ) and (file_link.endswith(".gz") or file_link.endswith(".xml")):
                file_save_path = (
                    file_save_path + "." + file_link.split("?")[0].split(".")[-1]
                )

            # Download file content
            try:
                file_save_path_with_ext = await self.retrieve_file(
                    file_link, file_save_path
                )
            except Exception as e:  # pylint: disable=broad-except
                Logger.warning(f"Error downloading {file_link}: {e}")
                file_save_path_with_ext = await self._wget_file(
                    file_link, file_save_path
                )
            downloaded = True

            # Read file content
            file_content = await asyncio.to_thread(
                self._read_file_content, file_save_path_with_ext
            )

            # Use the file output handler to save
            result = await self.storage_path.save_file(
                file_link=file_link,
                file_name=os.path.basename(file_save_path_with_ext),
                file_content=file_content,
                metadata={
                    "chain": self.chain.value,
                    "chain_id": self.chain_id,
                    "original_filename": file_name,
                },
            )

            # Clean up temporary file if we're using queue output
            if not isinstance(self.storage_path, DiskFileOutput):
                await asyncio.to_thread(os.remove, file_save_path_with_ext)

            return {
                "file_name": file_name,
                "downloaded": downloaded,
                "extract_succefully": result.get("extract_successfully", False),
                "error": result.get("error"),
                "restart_and_retry": False,
            }

        except RestartSessionError as exception:
            Logger.error(f"Error processing {file_link}, downloaded={downloaded}")
            Logger.error_execption(exception)
            error = str(exception)
            restart_and_retry = True
        except Exception as exception:  # pylint: disable=broad-except
            Logger.error(f"Error processing {file_link}, downloaded={downloaded}")
            Logger.error_execption(exception)
            error = str(exception)

        return {
            "file_name": file_name,
            "downloaded": downloaded,
            "extract_succefully": False,
            "error": error,
            "restart_and_retry": restart_and_retry,
        }

    def _read_file_content(self, file_path: str) -> bytes:
        """Read file content as bytes (sync operation for thread)."""
        with open(file_path, "rb") as f:
            return f.read()

    async def _wget_file(self, file_link, file_save_path):
        return await asyncio.to_thread(wget_file, file_link, file_save_path)

    async def _save_and_extract(self, file_link, file_save_path):
        downloaded = False
        extract_succefully = False
        error = None
        restart_and_retry = False
        try:

            # add ext if possible
            if not (
                file_save_path.endswith(".gz") or file_save_path.endswith(".xml")
            ) and (file_link.endswith(".gz") or file_link.endswith(".xml")):
                file_save_path = (
                    file_save_path + "." + file_link.split("?")[0].split(".")[-1]
                )

            # try to download the file
            try:
                file_save_path_with_ext = await self.retrieve_file(
                    file_link, file_save_path
                )
            except Exception as e:  # pylint: disable=broad-except
                Logger.warning(f"Error downloading {file_link}: {e}")
                file_save_path_with_ext = await self._wget_file(
                    file_link, file_save_path
                )
            downloaded = True

            if file_save_path_with_ext.endswith("gz"):
                Logger.debug(
                    f"File size is {os.path.getsize(file_save_path_with_ext)} bytes."
                )
                await asyncio.to_thread(
                    extract_xml_file_from_gz_file, file_save_path_with_ext
                )

                await asyncio.to_thread(os.remove, file_save_path_with_ext)
            extract_succefully = True

            Logger.debug(f"Done downloading {file_link}")
        except RestartSessionError as exception:
            Logger.error(
                f"Error downloading {file_link},extract_succefully={extract_succefully}"
                f",downloaded={downloaded}"
            )
            Logger.error_execption(exception)
            error = str(exception)
            restart_and_retry = True
        except Exception as exception:  # pylint: disable=broad-except
            Logger.error(
                f"Error downloading {file_link},extract_succefully={extract_succefully}"
                f",downloaded={downloaded}"
            )
            Logger.error_execption(exception)
            error = str(exception)

        return downloaded, extract_succefully, error, restart_and_retry
