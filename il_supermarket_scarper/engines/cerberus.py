import os
import datetime

from il_supermarket_scarper.utils import (
    extract_xml_file_from_gz_file,
    Logger,
    execute_in_parallel,
    collect_from_ftp,
    fetch_temporary_gz_file_from_ftp,
    FileTypesFilters,
)
from .engine import Engine


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

    def _scrape(
        self,
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        files_names_to_scrape=None,
        filter_null=False,
        filter_zero=False,
        suppress_exception=False,
    ):
        files = []
        try:
            files = self.collect_files_details_from_site(
                limit=limit,
                files_types=files_types,
                filter_null=filter_null,
                filter_zero=filter_zero,
                store_id=store_id,
                when_date=when_date,
                files_names_to_scrape=files_names_to_scrape,
                suppress_exception=suppress_exception,
            )
            self.on_collected_details(files)

            results = execute_in_parallel(
                self.persist_from_ftp, list(files), max_threads=self.max_threads
            )
            return results
        except Exception as e:  # pylint: disable=broad-except
            self.on_download_fail(e, files=files)
            raise e

    def get_type_pattern(self, files_types):
        """get the file type pattern"""
        file_type_mapping = {
            FileTypesFilters.STORE_FILE.name: "store",
            FileTypesFilters.PRICE_FILE.name: "price",
            FileTypesFilters.PROMO_FILE.name: "promo",
            FileTypesFilters.PRICE_FULL_FILE.name: "pricef",
            FileTypesFilters.PROMO_FULL_FILE.name: "promof",
        }
        if files_types is None or files_types == FileTypesFilters.all_types():
            return [None]

        responses = []
        for file_type in files_types:
            if file_type not in file_type_mapping:
                raise ValueError(f"File type {file_type} not supported")
            responses.append(file_type_mapping[file_type])
        return responses

    def build_filter_arg(self, store_id=None, when_date=None, files_types=None):
        """build the filter arg for the ftp"""
        date_pattern = None
        if when_date and isinstance(when_date, datetime.datetime):
            date_pattern = when_date.strftime("%Y%m%d")

        for type_pattern in self.get_type_pattern(files_types):
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

    def collect_files_details_from_site(
        self,
        limit=None,
        files_types=None,
        filter_null=False,
        filter_zero=False,
        store_id=None,
        when_date=None,
        files_names_to_scrape=None,
        suppress_exception=False,
    ):
        """collect all files to download from the site"""
        files = []
        for filter_arg in self.build_filter_arg(store_id, when_date, files_types):
            filter_files = collect_from_ftp(
                self.ftp_host,
                self.ftp_username,
                self.ftp_password,
                self.ftp_path,
                arg=filter_arg,
            )
            files.extend(filter_files)

        Logger.info(f"Found {len(files)} files")

        files = self.filter_bad_files(
            files, filter_null=filter_null, filter_zero=filter_zero
        )

        Logger.info(f"After filtering bad files: Found {len(files)} files")

        files = list(
            filter(lambda x: x.split(".")[-1] in self.target_file_extensions, files)
        )
        Logger.info(
            f"After filtering by {self.target_file_extensions}: Found {len(files)} files"
        )

        # apply noraml filter
        files = self.apply_limit(
            files,
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            when_date=when_date,
            files_names_to_scrape=files_names_to_scrape,
            suppress_exception=suppress_exception,
        )
        Logger.info(f"After applying limit: Found {len(files)} files")

        return files

    def persist_from_ftp(self, file_name):
        """download file to hard drive and extract it."""
        downloaded = False
        extract_succefully = False
        restart_and_retry = False
        error = None
        try:
            ext = os.path.splitext(file_name)[1]
            if ext not in [".gz", ".xml"]:
                raise ValueError(f"File {file_name} extension is not .gz or .xml")

            Logger.debug(f"Start persisting file {file_name}")
            temporary_gz_file_path = os.path.join(self.storage_path, file_name)

            fetch_temporary_gz_file_from_ftp(
                self.ftp_host,
                self.ftp_username,
                self.ftp_password,
                self.ftp_path,
                temporary_gz_file_path,
                timeout=30,
            )
            downloaded = True

            if ext == ".gz":
                Logger.debug(
                    f"File size is {os.path.getsize(temporary_gz_file_path)} bytes."
                )
                extract_xml_file_from_gz_file(temporary_gz_file_path)

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
            if ext == ".gz" and os.path.exists(temporary_gz_file_path):
                os.remove(temporary_gz_file_path)

        return {
            "file_name": file_name,
            "downloaded": downloaded,
            "extract_succefully": extract_succefully,
            "restart_and_retry": restart_and_retry,
            "error": error,
        }
