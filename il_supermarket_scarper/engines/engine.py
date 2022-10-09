from urllib.request import urlretrieve
from abc import ABC
import os


from il_supermarket_scarper.utils import (
    get_output_folder,
    FileTypesFilters,
    Logger,
    ScraperStatus,
    extract_xml_file_from_gz_file,
    download_connection_retry,
    session_with_cookies,
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
        return limit == 0 or files_types == []

    def apply_limit(
        self, intreable, limit=None, files_types=None, by_function=lambda x: x
    ):
        """filter the list according to condition"""
        intreable_ = self.filter_already_downloaded(
            self.storage_path, intreable, by_function=by_function
        )
        files_was_filtered_since_already_download = (
            len(list(intreable)) != 0 and len(list(intreable_)) == 0
        )
        intreable_ = self.unique(intreable_, by_function=by_function)
        if files_types:
            intreable_ = []
            for type_ in files_types:
                type_files = FileTypesFilters.filter(
                    type_, intreable, by_function=by_function
                )
                if limit:
                    type_files = type_files[: min(limit, len(type_files))]
                intreable_.extend(type_files)

        elif limit:
            assert limit > 0, "Limit must be greater than 0"
            Logger.info(f"Limit: {limit}")
            intreable_ = intreable_[: min(limit, len(list(intreable_)))]
        Logger.info(f"Result length {len(list(intreable_))}")

        if len(list(intreable_)) == 0:
            if not (
                files_was_filtered_since_already_download
                or self.is_validate_scraper_found_no_files(
                    limit=limit, files_types=files_types
                )
            ):
                raise ValueError(f"No files to download for file {files_types}")
        return intreable_

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

    def session_with_cookies_by_chain(self, url):
        """request resource with cookie by chain name"""
        return session_with_cookies(self.chain, url)

    def post_scraping(self):
        """job to do post scraping"""
        cookie_file = f"{self.chain}_cookies.txt"
        if os.path.exists(cookie_file):
            os.remove(cookie_file)

    def scrape(self, limit=None, files_types=None):
        """run the scraping logic"""
        self.post_scraping()
        self.on_scraping_start(limit=limit, files_types=files_types)
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

    @download_connection_retry()
    def retrieve_file(self, file_link, file_save_path):
        """download file"""
        file_save_path_res = (
            file_save_path + "." + file_link.split("?")[0].split(".")[-1]
        )
        urlretrieve(file_link, file_save_path_res)
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
            Logger.error(exception)
            error = str(exception)

        return downloaded, extract_succefully, error
