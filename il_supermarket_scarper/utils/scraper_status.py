import os

from .logger import Logger
from .status import log_folder_details
from .databases import JsonDataBase
from .status import _now


class ScraperStatus:
    """A class that abstracts the database interface for scraper status."""

    STARTED = "started"
    COLLECTED = "collected"
    DOWNLOADED = "downloaded"
    ESTIMATED_SIZE = "estimated_size"

    def __init__(self, database_name, base_path) -> None:
        self.database = JsonDataBase(database_name, base_path)

    def on_scraping_start(self, limit, files_types, **additional_info):
        """Report that scraping has started."""
        self._insert_an_update(
            ScraperStatus.STARTED,
            limit=limit,
            files_requested=files_types,
            **additional_info,
        )

    def on_collected_details(
        self,
        file_name_collected_from_site,
        links_collected_from_site="",
        **additional_info,
    ):
        """Report that file details have been collected."""
        self._insert_an_update(
            ScraperStatus.COLLECTED,
            file_name_collected_from_site=file_name_collected_from_site,
            links_collected_from_site=links_collected_from_site,
            **additional_info,
        )

    def on_download_completed(self, **additional_info):
        """Report that the file has been downloaded."""
        self._insert_an_update(ScraperStatus.DOWNLOADED, **additional_info)
        self._add_downloaded_files_to_list(**additional_info)

    def filter_already_downloaded(
        self, storage_path, files_names_to_scrape, filelist, by_function=lambda x: x
    ):
        """Filter files already existing in long-term memory or previously downloaded."""
        if self.database.is_collection_enabled():
            new_filelist = []
            for file in filelist:
                if not self.database.find_document(
                    "scraper_download", {"file_name": by_function(file)}
                ):
                    new_filelist.append(file)
                else:
                    Logger.info(
                        f"Filtered file {file} since it was already downloaded and extracted"
                    )
            return new_filelist

        # Fallback: filter according to the disk
        exits_on_disk = os.listdir(storage_path)

        if files_names_to_scrape:
            # Delete any files we want to retry downloading
            for file in exits_on_disk:
                if file.split(".")[0] in files_names_to_scrape:
                    os.remove(os.path.join(storage_path, file))

            # Filter the files to download
            filelist = list(
                filter(lambda x: by_function(x) in files_names_to_scrape, filelist)
            )

        return list(filter(lambda x: by_function(x) not in exits_on_disk, filelist))

    def _add_downloaded_files_to_list(self, results, **_):
        """Add downloaded files to the MongoDB collection."""
        if self.database.is_collection_enabled():
            when = _now()
            for res in results:
                if res["downloaded"] and res["extract_succefully"]:
                    self.database.insert_document(
                        "scraper_download",
                        {"file_name": res["file_name"], "when": when},
                    )

    def on_scrape_completed(self, folder_name):
        """Report when scraping is completed."""
        self._insert_an_update(
            ScraperStatus.ESTIMATED_SIZE, folder_size=log_folder_details(folder_name)
        )

    def _insert_an_update(self, status, **additional_info):
        """Insert an update into the MongoDB collection."""
        document = {
            "status": status,
            "when": _now(),
            **additional_info,
        }
        self.database.insert_document("scraper_status", document)
