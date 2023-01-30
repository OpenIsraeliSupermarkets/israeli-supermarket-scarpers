from abc import ABC
import os


from il_supermarket_scarper.utils import (
    get_output_folder,
    FileTypesFilters,
    Logger,
    ScraperStatus,
    extract_xml_file_from_gz_file,
    url_connection_retry,
    session_with_cookies,
    url_retrieve,
)


class Engine(ScraperStatus, ABC):
    """base engine for scraping"""

    def __init__(
        self,
        chain,
        chain_id,
        folder_name=None,
    ):
        super().__init__(chain)
        self.chain = chain
        self.chain_id = chain_id
        self.max_workers = 5
        if folder_name:
            self.storage_path = os.path.join(folder_name, self.chain)
        else:
            self.storage_path = get_output_folder(self.chain)
        Logger.info(f"Storage path: {self.storage_path}")

    def get_storage_path(self):
        """the the storage page of the files downloaded"""
        return self.storage_path

    def is_validate_scraper_found_no_files(self, limit=None, files_types=None):
        """return true if its ok the scarper reuturn no enrty"""

        # if all the files requested are the update files, is ok the scaraper failed.
        request_only_update_file = False
        if files_types:
            request_only_update_file = True
            for file_type in files_types:
                if file_type in FileTypesFilters.all_full_files():
                    request_only_update_file = False

        return limit == 0 or files_types == [] or request_only_update_file

    def is_valid_file_empty(self, file_name):
        """it is valid the file is empty"""
        return file_name is None

    def apply_limit(
        self,
        intreable,
        limit=None,
        files_types=None,
        by_function=lambda x: x,
        store_id=None,
        only_latest=False,
    ):
        """filter the list according to condition"""
        assert (
            not only_latest or limit is None
        ), "only_latest flag can't be applied with limit."

        # filter files already downloaded
        intreable_ = self.filter_already_downloaded(
            self.storage_path, intreable, by_function=by_function
        )
        files_was_filtered_since_already_download = (
            len(list(intreable)) != 0 and len(list(intreable_)) == 0
        )

        # filter unique links
        intreable_ = self.unique(intreable_, by_function=by_function)

        # filter by store id
        if store_id:
            intreable_ = list(
                filter(lambda x: f"{store_id:03d}-" in by_function(x), intreable_)
            )

        # filter by file type
        if files_types:
            intreable_ = self.filter_file_types(
                intreable, limit, files_types, by_function
            )
        if only_latest:
            intreable_ = self.get_only_latest(by_function, intreable_)

        # filter by limit if the 'files_types' filter is not on.
        if limit and files_types is None:
            assert limit > 0, "Limit must be greater than 0"
            Logger.info(f"Limit: {limit}")
            intreable_ = intreable_[: min(limit, len(list(intreable_)))]
        Logger.info(f"Result length {len(list(intreable_))}")

        # raise error if there was nothing to download.
        if len(list(intreable_)) == 0:
            if not (
                files_was_filtered_since_already_download
                or self.is_validate_scraper_found_no_files(
                    limit=limit, files_types=files_types
                )
            ):
                raise ValueError(f"No files to download for file {files_types}")
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

    def session_with_cookies_by_chain(self, url, timeout=15):
        """request resource with cookie by chain name"""
        return session_with_cookies(url, chain_cookie_name=self.chain, timeout=timeout)

    def post_scraping(self):
        """job to do post scraping"""
        cookie_file = f"{self.chain}_cookies.txt"
        if os.path.exists(cookie_file):
            os.remove(cookie_file)

    def scrape(self, limit=None, files_types=None, store_id=None, only_latest=False):
        """run the scraping logic"""
        self.post_scraping()
        self.on_scraping_start(
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            only_latest=only_latest,
        )
        Logger.info(f"Starting scraping for {self.chain}")
        self.make_storage_path_dir()

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
        file_save_path_res = (
            file_save_path + "." + file_link.split("?")[0].split(".")[-1]
        )
        url_retrieve(file_link, file_save_path_res, timeout=timeout)
        return file_save_path_res

    def save_and_extract(self, arg):
        """download file and extract it"""

        file_link, file_name = arg
        file_save_path = os.path.join(self.storage_path, file_name)
        Logger.info(f"Downloading {file_link} to {file_save_path}")
        downloaded, extract_succefully, error = self._save_and_extract(
            file_link, file_save_path
        )

        return {
            "file_name": file_name,
            "downloaded": downloaded,
            "extract_succefully": extract_succefully,
            "error": error,
        }

    def _save_and_extract(self, file_link, file_save_path):
        downloaded = False
        extract_succefully = False
        error = None
        try:
            file_save_path_with_ext = self.retrieve_file(file_link, file_save_path)
            downloaded = True

            if file_save_path_with_ext.endswith("gz"):
                extract_xml_file_from_gz_file(file_save_path_with_ext)

                os.remove(file_save_path_with_ext)
            extract_succefully = True

            Logger.info(f"Done downloading {file_link}")

        except Exception as exception:  # pylint: disable=broad-except
            Logger.error(
                f"Error downloading {file_link},extract_succefully={extract_succefully}"
                f",downloaded={downloaded}"
            )
            Logger.error_execption(exception)
            error = str(exception)

        return downloaded, extract_succefully, error
