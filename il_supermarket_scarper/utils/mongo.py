import datetime
import os
import uuid
from .logger import Logger
from .status import log_folder_details

PYMONGO_INSTALLED = True
try:
    import pymongo
    from pymongo.errors import ServerSelectionTimeoutError
except ImportError:
    PYMONGO_INSTALLED = False

class MongoDataBase:
    """A class that represents a MongoDB database."""

    def __init__(self, database_name) -> None:
        self.myclient = None
        self.collection_status = False
        self.database_name = database_name.replace(" ", "_").lower()
        self.store_db = None
    
    def is_collection_enabled(self):
        return self.collection_status
    
    def create_connection(self):
        """Create a connection to the MongoDB database."""
        if PYMONGO_INSTALLED:
            url = os.environ.get("MONGO_URL", "localhost")
            port = os.environ.get("MONGO_PORT", "27017")
            self.myclient = pymongo.MongoClient(f"mongodb://{url}:{port}/")
            self.store_db = self.myclient[self.database_name]

    def enable_collection_status(self):
        """Enable data collection to MongoDB."""
        if PYMONGO_INSTALLED:
            self.collection_status = True
            self.create_connection()
        else:
            Logger.info("Can't enable collection. Please install pymongo.")

    def insert_document(self, collection_name, document):
        """Insert a document into a MongoDB collection."""
        if self.collection_status:
            try:
                self.store_db[collection_name].insert_one(document)
            except ServerSelectionTimeoutError:
                self.collection_status = False
                Logger.error("Failed to connect to MongoDB. Collection status disabled.")

    def find_document(self, collection_name, query):
        """Find a document in a MongoDB collection."""
        if self.collection_status:
            return self.store_db[collection_name].find_one(query)
        return None


class ScraperStatus:
    """A class that abstracts the database interface for scraper status."""

    STARTED = "started"
    COLLECTED = "collected"
    DOWNLOADED = "downloaded"
    ESTIMATED_SIZE = "estimated_size"

    def __init__(self, database_name) -> None:
        self.database = MongoDataBase(database_name)
        self.instance_id = uuid.uuid4().hex

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
        links_collected_from_site="FTP_ACCESS_LINK_MEANINGLESS",
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
            when = datetime.datetime.now()
            for res in results:
                if res["downloaded"] and res["extract_succefully"]:
                    self.database.insert_document(
                        "scraper_download", {"file_name": res["file_name"], "when": when}
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
            "when": datetime.datetime.now(),
            **additional_info,
        }
        self.database.insert_document("scraper_status", document)
