from abc import ABC, abstractmethod
import os
import re
import random
import uuid
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
        self.assigned_cookie = f"{self.chain.name}_{uuid.uuid4()}_cookies.txt"

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
        random_selection=False,
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
                intreable_,
                limit,
                files_types,
                by_function,
                random_selection=random_selection,
            )
        Logger.info(f"Number of entry after filter file type id is {len(intreable_)}")

        # Warning and filtering for random_selection
        if random_selection:
            Logger.warning(
                "random_selection is enabled. Will select only from files from the last 48 hours."
            )

        if isinstance(when_date, datetime.datetime):
            intreable_ = self.get_by_date(when_date, by_function, intreable_)
        elif isinstance(when_date, str) and when_date == "latest":
            intreable_ = self.get_only_latest(by_function, intreable_)
        elif when_date is not None:
            raise ValueError(
                f"when_date should be datetime or 'latest', got {when_date}"
            )
        elif random_selection:
            # Filter to last 48 hours when random_selection is used and no when_date is specified
            intreable_ = self.apply_limit_random_selection(
                intreable_, limit, by_function
            )

        Logger.info(
            f"Number of entry after filtering base on time is {len(intreable_)}"
        )

        # filter by limit if the 'files_types' filter is not on.
        if limit:
            assert limit > 0, "Limit must be greater than 0"
            Logger.info(f"Limit: {limit}")
            intreable_list = list(intreable_)
            if random_selection and len(intreable_list) > limit:
                intreable_ = random.sample(intreable_list, limit)
            else:
                intreable_ = intreable_list[: min(limit, len(intreable_list))]
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

    def apply_limit_random_selection(self, intreable, limit, by_function):
        """apply limit to the intreable"""
        intreable_ = self.get_last_48_hours(by_function, intreable)
        if len(intreable_) > limit:
            return random.sample(intreable_, limit)
        return intreable_[: min(limit, len(intreable_))]

    def filter_file_types(
        self, intreable, limit, files_types, by_function, random_selection=False
    ):
        """filter the file types requested"""
        intreable_ = []
        for type_ in files_types:
            type_files = FileTypesFilters.filter(
                type_, intreable, by_function=by_function
            )
            if limit:
                if random_selection:
                    type_files = self.apply_limit_random_selection(
                        type_files, limit, by_function
                    )
                else:
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

    def get_last_48_hours(self, by_function, intreable_):
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

    async def session_with_cookies_by_chain(
        self, url, method="GET", body=None, timeout=15, headers=None
    ):
        """request resource with cookie by chain name"""
        return await session_with_cookies(
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
                min_size=min_size,
                max_size=max_size,
                random_selection=random_selection,
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
        min_size=None,
        max_size=None,
        random_selection=False,
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

    def get_file_size_from_entry(self, entry):  # pylint: disable=unused-argument
        """
        Extract file size from an entry (table row).
        Returns file size in bytes, or None if size information is not available.
        Default implementation returns None - should be overridden by subclasses.
        """
        return None

    def filter_by_file_size(
        self, file_names, download_urls, file_sizes, min_size=None, max_size=None
    ):
        """
        Filter files by size (in bytes).
        Returns filtered (file_names, download_urls, file_sizes) tuples.
        Entries with None file_size are kept by default.
        """
        if min_size is None and max_size is None:
            return file_names, download_urls, file_sizes

        filtered_names = []
        filtered_urls = []
        filtered_sizes = []

        for name, url, size in zip(file_names, download_urls, file_sizes):
            # Keep entries with None size (can't filter them)
            if size is None:
                filtered_names.append(name)
                filtered_urls.append(url)
                filtered_sizes.append(size)
            else:
                # Apply size filters
                if min_size is not None and size < min_size:
                    continue
                if max_size is not None and size > max_size:
                    continue
                filtered_names.append(name)
                filtered_urls.append(url)
                filtered_sizes.append(size)

        Logger.info(
            f"After filtering by file size (min={min_size}, max={max_size}): "
            f"Found {len(filtered_names)} files (from {len(file_names)})"
        )
        return filtered_names, filtered_urls, filtered_sizes

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

    def _wget_file(self, file_link, file_save_path):
        return wget_file(file_link, file_save_path)

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
                file_save_path_with_ext = self._wget_file(file_link, file_save_path)
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
