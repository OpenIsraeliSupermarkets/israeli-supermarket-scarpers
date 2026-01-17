import datetime
from typing import AsyncGenerator, List
from il_supermarket_scarper.utils import (
    Logger,
    collect_from_ftp,
    fetch_file_from_ftp_to_memory,
    FileTypesFilters,
    ScrapingResult,
)
from il_supermarket_scarper.utils.state import FilterState
from .engine import Engine


class Cerberus(Engine):
    """scraper for all Cerberus base site. (seems like can't support historical data)"""

    target_file_extensions = ["xml", "gz"]
    utilize_date_param = False

    def __init__(
        self,
        chain,
        chain_id,
        ftp_host="url.retail.publishedprices.co.il",
        ftp_path="/",
        ftp_username="",
        ftp_password="",
        max_threads=5,
        file_output=None,
        status_database=None,
    ):
        super().__init__(
            chain,
            chain_id,
            max_threads,
            file_output=file_output,
            status_database=status_database,
        )
        self.ftp_host = ftp_host
        self.ftp_path = ftp_path
        self.ftp_username = ftp_username
        self.ftp_password = ftp_password
        self.ftp_session = False

    async def process_file(self, file_details):
        """Process a single file from Cerberus. file_details is file_name string."""
        file_name = file_details

        # Register that we've collected this file's details
        self.register_collected_file(
            file_name_collected_from_site=file_name[0],
            links_collected_from_site="",
        )

        # Process file from FTP - persist_from_ftp yields a ScrapingResult
        async for result in self.persist_from_ftp(file_name[0]):
            return result

        # Should not reach here, but return error result if we do
        return ScrapingResult(
            file_name=file_name[0],
            downloaded=False,
            extract_succefully=False,
            error="No result from persist_from_ftp",
            restart_and_retry=False,
        )

    async def get_type_pattern(self, files_types):
        """get the file type pattern"""
        file_type_mapping = {
            FileTypesFilters.STORE_FILE.name: "store",
            FileTypesFilters.PRICE_FILE.name: "price",
            FileTypesFilters.PROMO_FILE.name: "promo",
            FileTypesFilters.PRICE_FULL_FILE.name: "pricef",
            FileTypesFilters.PROMO_FULL_FILE.name: "promof",
        }
        if files_types is None or files_types == FileTypesFilters.all_types():
            yield None
            return

        for file_type in files_types:
            if file_type not in file_type_mapping:
                raise ValueError(f"File type {file_type} not supported")
            yield file_type_mapping[file_type]

    async def build_filter_arg(self, store_id=None, when_date=None, files_types=None):
        """build the filter arg for the ftp"""
        date_pattern = None
        if when_date and isinstance(when_date, datetime.datetime):
            date_pattern = when_date.strftime("%Y%m%d")

        async for type_pattern in self.get_type_pattern(files_types):
            output_pattern = []
            if type_pattern:
                output_pattern.append(type_pattern)
            if store_id:
                output_pattern.append(f"{store_id}-")
            if date_pattern:
                output_pattern.append(date_pattern)

            if len(output_pattern) == 0:
                yield None
            yield "*" + "*".join(output_pattern) + "*"

    def is_file_extension_valid(self, file_name):
        """check if the file extension is valid"""
        return file_name.split(".")[-1] in self.target_file_extensions

    async def filter_by_file_extension(
        self, files: AsyncGenerator[tuple[str, str, int], None]
    ):
        """filter the files by the file extension"""
        async for file in files:
            if not self.is_file_extension_valid(file[0]):
                continue
            yield file

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
        """collect all files to download from the site"""

        async for filter_arg in self.build_filter_arg(store_id, when_date, files_types):
            # Get async generator from FTP
            files_generator = collect_from_ftp(
                self.ftp_host,
                self.ftp_username,
                self.ftp_password,
                self.ftp_path,
                filter_arg,
            )

            files: AsyncGenerator[List[str, str], None] = self.filter_by_file_size(
                files_generator,
                min_size=min_size,
                max_size=max_size,
            )

            files = self.filter_bad_files(
                files,
                filter_null=filter_null,
                filter_zero=filter_zero,
                by_function=lambda x: x[0],
            )

            files: AsyncGenerator[tuple[str, str, int], None] = (
                self.filter_by_file_extension(files)
            )

            # apply noraml filter
            async for file in self.apply_limit(
                state,
                files,
                limit=limit,
                files_types=files_types,
                store_id=store_id,
                when_date=when_date,
                files_names_to_scrape=files_names_to_scrape,
                by_function=lambda x: x[0],
            ):
                yield file

    async def persist_from_ftp(self, file_name):
        """download file to memory and extract it."""
        downloaded = False
        extract_succefully = False
        restart_and_retry = False
        error = None
        ext = None
        try:
            ext = file_name.split(".")[-1] if "." in file_name else ""
            if ext not in ["gz", "xml"]:
                raise ValueError(f"File {file_name} extension is not .gz or .xml")

            Logger.debug(f"Start persisting file {file_name} (in-memory)")

            # Download file directly to memory
            file_content = await fetch_file_from_ftp_to_memory(
                self.ftp_host,
                self.ftp_username,
                self.ftp_password,
                self.ftp_path,
                file_name,
                30,
            )
            downloaded = True

            if ext == "gz":
                Logger.debug(f"File size is {len(file_content)} bytes.")

            # Use the file output handler to save
            result = await self.storage_path.save_file(
                file_link="",  # FTP doesn't have a URL
                file_name=file_name,
                file_content=file_content,
                metadata={
                    "chain": self.chain.value,
                    "chain_id": self.chain_id,
                    "original_filename": file_name,
                    "source": "ftp",
                },
            )

            Logger.debug(f"Done persisting file {file_name}")
            extract_succefully = result.get("extract_successfully", False)
            error = result.get("error")
        except Exception as exception:  # pylint: disable=broad-except
            Logger.error(
                f"Error downloading {file_name},extract_succefully={extract_succefully}"
                f",downloaded={downloaded}"
            )
            Logger.error_execption(exception)
            error = str(exception)
            restart_and_retry = True

        yield ScrapingResult(
            file_name=file_name,
            downloaded=downloaded,
            extract_succefully=extract_succefully,
            restart_and_retry=restart_and_retry,
            error=error,
        )
