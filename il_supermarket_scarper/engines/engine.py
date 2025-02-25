from abc import ABC, abstractmethod
import os
import re
import datetime

from il_supermarket_scarper.utils import (
    get_output_folder,
    FileTypesFilters,
    Logger,
    ScraperStatus,
    extract_xml_file_from_gz_file,
    url_connection_retry,
    session_with_cookies,
    url_retrieve,
    wget_file,
    RestartSessionError,
    DumpFolderNames,
)


class Engine(ScraperStatus, ABC):
    """base engine for scraping"""

    utilize_date_param = True

    def __init__(self, chain, chain_id, folder_name=None, max_threads=10):
        assert DumpFolderNames.is_valid_folder_name(
            chain
        ), "chain name can contain only abc and -"

        super().__init__(chain.value, "status", folder_name=folder_name)
        self.chain = chain
        self.chain_id = chain_id
        self.max_threads = max_threads
        self.storage_path = get_output_folder(self.chain.value, folder_name=folder_name)
        self.assigned_cookie = f"{self.chain.name}_{id(self)}_cookies.txt"

    def get_storage_path(self):
        """the the storage page of the files downloaded"""
        return self.storage_path

    def is_valid_file_empty(self, file_name):
        """it is valid the file is empty"""
        return file_name is None

    def filter_bad_files(
        self, files, filter_zero=False, filter_null=False, by_function=lambda x: x
    ):
        """filter out bad files"""

        if filter_zero:
            files = list(
                filter(lambda x: "0000000000000" not in by_function(x), files)
            )  # filter out files
            Logger.info(
                f"After filtering with '0000000000000': Found {len(files)} files"
            )

        if filter_null:
            files = list(
                filter(lambda x: "NULL" not in by_function(x), files)
            )  # filter out files
            Logger.info(f"After filtering with 'NULL': Found {len(files)} files")

        return files

    def apply_limit(
        self,
        intreable,
        limit=None,
        files_types=None,
        by_function=lambda x: x,
        store_id=None,
        when_date=None,
        files_names_to_scrape=None,
        suppress_exception=False,
    ):
        """filter the list according to condition"""

        # filter files already downloaded
        intreable_ = self.filter_already_downloaded(
            self.storage_path, files_names_to_scrape, intreable, by_function=by_function
        )
        Logger.info(
            f"Number of entry after filter already downloaded is {len(intreable_)}"
        )
        files_was_filtered_since_already_download = (
            len(list(intreable)) != 0 and len(list(intreable_)) == 0
        )

        # filter unique links
        intreable_ = self.unique(intreable_, by_function=by_function)
        Logger.info(f"Number of entry after filter unique links is {len(intreable_)}")

        # filter by store id
        if store_id:
            pattern = re.compile(rf"-0*{store_id}-")
            intreable_ = list(
                filter(
                    lambda x: pattern.search(by_function(x)),
                    intreable_,
                )
            )
        Logger.info(f"Number of entry after filter store id is {len(intreable_)}")

        # filter by file type
        if files_types:
            intreable_ = self.filter_file_types(
                intreable_, limit, files_types, by_function
            )
        Logger.info(f"Number of entry after filter file type id is {len(intreable_)}")

        if isinstance(when_date, datetime.datetime):
            intreable_ = self.get_by_date(when_date, by_function, intreable_)
        elif isinstance(when_date, str) and when_date == "latest":
            intreable_ = self.get_only_latest(by_function, intreable_)
        elif when_date is not None:
            raise ValueError(
                f"when_date should be datetime or 'latest', got {when_date}"
            )

        Logger.info(
            f"Number of entry after filtering base on time is {len(intreable_)}"
        )

        # filter by limit if the 'files_types' filter is not on.
        if limit:
            assert limit > 0, "Limit must be greater than 0"
            Logger.info(f"Limit: {limit}")
            intreable_ = intreable_[: min(limit, len(list(intreable_)))]
        Logger.info(f"Result length {len(list(intreable_))}")

        # raise error if there was nothing to download.
        if len(list(intreable_)) == 0 and not files_was_filtered_since_already_download:
            if not suppress_exception:
                raise ValueError(
                    f"No files to download for file files_types={files_types},"
                    f"limit={limit},store_id={store_id},when_date={when_date}"
                )
            Logger.warning(
                f"No files to download for file files_types={files_types},"
                f"limit={limit},store_id={store_id},when_date={when_date}"
            )
        return intreable_

    def filter_file_types(self, intreable, limit, files_types, by_function):
        """filter the file types requested"""
        intreable_ = []
        for type_ in files_types:
            type_files = FileTypesFilters.filter(
                type_, intreable, by_function=by_function
            )
            if limit:
                type_files = type_files[: min(limit, len(type_files))]
            intreable_.extend(type_files)
        return intreable_

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

    def get_by_date(self, requested_date, by_function, intreable_):
        """get by date"""
        #
        date_format = requested_date.strftime("%Y%m%d")
        #
        groups_value = []
        for file in intreable_:
            # StoresFull7290875100001-000-202502250510'
            # Promo7290700100008-000-207-20250224-103225
            if f"-{date_format}" in by_function(file):
                groups_value.append(file)

        return groups_value

    @classmethod
    def unique(cls, iterable, by_function=lambda x: x):
        """Returns the type of the file."""
        seen = set()
        result = []
        for item in iterable:
            k = by_function(item)
            if k not in seen:
                seen.add(k)
                result.append(item)

        return result

    def session_with_cookies_by_chain(self, url, method="GET", body=None, timeout=15):
        """request resource with cookie by chain name"""
        return session_with_cookies(
            url,
            chain_cookie_name=self.assigned_cookie,
            timeout=timeout,
            method=method,
            body=body,
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

    def scrape(
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
        self.make_storage_path_dir()
        completed_successfully = True
        results = []
        try:
            results = self._scrape(
                limit=limit,
                files_types=files_types,
                store_id=store_id,
                when_date=when_date,
                files_names_to_scrape=files_names_to_scrape,
                filter_null=filter_null,
                filter_zero=filter_zero,
                suppress_exception=suppress_exception,
            )
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
        """method to be implemeted by the child class"""

    def make_storage_path_dir(self):
        """create the storage path"""
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

    def get_chain_id(self):
        """get the chain id as list"""
        if isinstance(self.chain_id, list):
            return self.chain_id
        return [self.chain_id]

    def get_chain_name(self):
        """return chain name"""
        return self.chain

    @url_connection_retry()
    def retrieve_file(self, file_link, file_save_path, timeout=30):
        """download file"""
        url_retrieve(file_link, file_save_path, timeout=timeout)
        return file_save_path

    def save_and_extract(self, arg):
        """download file and extract it"""

        file_link, file_name = arg
        file_save_path = os.path.join(self.storage_path, file_name)
        Logger.debug(f"Downloading {file_link} to {file_save_path}")
        (
            downloaded,
            extract_succefully,
            error,
            restart_and_retry,
        ) = self._save_and_extract(file_link, file_save_path)

        return {
            "file_name": file_name,
            "downloaded": downloaded,
            "extract_succefully": extract_succefully,
            "error": error,
            "restart_and_retry": restart_and_retry,
        }

    def _save_and_extract(self, file_link, file_save_path):
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
                file_save_path_with_ext = self.retrieve_file(file_link, file_save_path)
            except Exception as e:  # pylint: disable=broad-except
                Logger.warning(f"Error downloading {file_link}: {e}")
                file_save_path_with_ext = wget_file(file_link, file_save_path)
            downloaded = True

            if file_save_path_with_ext.endswith("gz"):
                Logger.debug(
                    f"File size is {os.path.getsize(file_save_path_with_ext)} bytes."
                )
                extract_xml_file_from_gz_file(file_save_path_with_ext)

                os.remove(file_save_path_with_ext)
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
