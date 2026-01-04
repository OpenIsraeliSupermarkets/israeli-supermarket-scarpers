import os
import datetime
import asyncio
from typing import AsyncGenerator, List
from il_supermarket_scarper.utils import (
    extract_xml_file_from_gz_file,
    Logger,
    collect_from_ftp,
    fetch_temporary_gz_file_from_ftp,
    FileTypesFilters,
)
from .engine import Engine
from il_supermarket_scarper.utils.state import FilterState


class Cerberus(Engine):
    """scraper for all Cerberus base site. (seems like can't support historical data)"""

    target_file_extensions = ["xml", "gz"]
    utilize_date_param = False

    def __init__(
        self,
        chain,
        chain_id,
        folder_name=None,
        ftp_host="url.retail.publishedprices.co.il",
        ftp_path="/",
        ftp_username="",
        ftp_password="",
        max_threads=5,
    ):
        super().__init__(chain, chain_id, folder_name, max_threads)
        self.ftp_host = ftp_host
        self.ftp_path = ftp_path
        self.ftp_username = ftp_username
        self.ftp_password = ftp_password
        self.ftp_session = False

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
        files = []
        try:
            async for file_name in self.collect_files_details_from_site(
                limit=limit,
                files_types=files_types,
                filter_null=filter_null,
                filter_zero=filter_zero,
                store_id=store_id,
                when_date=when_date,
                files_names_to_scrape=files_names_to_scrape,
                suppress_exception=suppress_exception,
                min_size=min_size,
                max_size=max_size,
                random_selection=random_selection,
            ):
                files.append(file_name)
                yield await self.persist_from_ftp(file_name)
        except Exception as e:  # pylint: disable=broad-except
            self.on_download_fail(e, file_names=files)
            raise e

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

    async def collect_files_details_from_site(  # pylint: disable=too-many-locals
        self,
        limit=None,
        files_types=None,
        filter_null=False,
        filter_zero=False,
        store_id=None,
        when_date=None,
        files_names_to_scrape=None,
        suppress_exception=False,
        min_size=None,
        max_size=None,
        random_selection=False,
    ):
        """collect all files to download from the site"""

        state = FilterState()
        async for filter_arg in self.build_filter_arg(store_id, when_date, files_types):
            # Get async generator from FTP
            files_generator = collect_from_ftp(
                self.ftp_host,
                self.ftp_username,
                self.ftp_password,
                self.ftp_path,
                filter_arg,
            )

            # Convert (filename, size) -> (filename, url_placeholder, size)
            async def convert_to_async_gen(files_gen):
                async for filename, size in files_gen:
                    # For FTP files, we don't have a URL yet, so use empty string as placeholder
                    yield (filename, "", size)

            files: AsyncGenerator[List[str, str], None] = self.filter_by_file_size(
                convert_to_async_gen(files_generator),
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
            files_gen = self.apply_limit(
                state,
                files,
                limit=limit,
                files_types=files_types,
                store_id=store_id,
                when_date=when_date,
                files_names_to_scrape=files_names_to_scrape,
                suppress_exception=suppress_exception,
                by_function=lambda x: x[0],
                random_selection=random_selection,
            )

            # Stream files and count them
            file_count = 0
            async for filename, _, _ in files_gen:
                file_count += 1
                yield filename

    async def persist_from_ftp(self, file_name):
        """download file to hard drive and extract it."""
        downloaded = False
        extract_succefully = False
        restart_and_retry = False
        error = None
        ext = None
        temporary_gz_file_path = None
        try:
            ext = os.path.splitext(file_name)[1]
            if ext not in [".gz", ".xml"]:
                raise ValueError(f"File {file_name} extension is not .gz or .xml")

            Logger.debug(f"Start persisting file {file_name}")
            temporary_gz_file_path = os.path.join(self.storage_path, file_name)

            await asyncio.to_thread(
                fetch_temporary_gz_file_from_ftp,
                self.ftp_host,
                self.ftp_username,
                self.ftp_password,
                self.ftp_path,
                temporary_gz_file_path,
                30,
            )
            downloaded = True

            if ext == ".gz":
                Logger.debug(
                    f"File size is {os.path.getsize(temporary_gz_file_path)} bytes."
                )
                await asyncio.to_thread(
                    extract_xml_file_from_gz_file, temporary_gz_file_path
                )

            Logger.debug(f"Done persisting file {file_name}")
            extract_succefully = True
        except Exception as exception:  # pylint: disable=broad-except
            Logger.error(
                f"Error downloading {file_name},extract_succefully={extract_succefully}"
                f",downloaded={downloaded}"
            )
            Logger.error_execption(exception)
            error = str(exception)
            restart_and_retry = True
        finally:
            if (
                ext == ".gz"
                and temporary_gz_file_path
                and os.path.exists(temporary_gz_file_path)
            ):
                await asyncio.to_thread(os.remove, temporary_gz_file_path)

        return {
            "file_name": file_name,
            "downloaded": downloaded,
            "extract_succefully": extract_succefully,
            "restart_and_retry": restart_and_retry,
            "error": error,
        }
