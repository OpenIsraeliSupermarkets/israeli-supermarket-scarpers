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


class DataBase:
    """a class represnt a database"""

    def __init__(self) -> None:
        self.myclient = None
        self.collection_status = False

    def create_connection(self):
        """create the connection"""
        if PYMONGO_INSTALLED:
            url = os.environ.get("MONGO_URL", "localhost")
            port = os.environ.get("MONGO_PORT", "27017")
            self.myclient = pymongo.MongoClient(f"mongodb://{url}:{port}/")

    def enable_collection_status(self):
        """try to enable data colllection to mongo"""
        if PYMONGO_INSTALLED:
            self.collection_status = True
            self.create_connection()
        else:
            Logger.info("can't able collection please install pymongo")


class ScraperStatus(DataBase):
    """class that abstract the database interface"""

    STARTED = "started"
    COLLECTED = "collected"
    DOWNLOADED = "downloaded"
    ESTIMATED_SIZE = "estimated_size"

    def __init__(self, database) -> None:
        super().__init__()
        self.database = database.replace(" ", "_").lower()
        self.instance_id = uuid.uuid4().hex

    def on_scraping_start(self, limit, files_types, **additional_info):
        """report scrap start"""
        self._insert_an_update(
            ScraperStatus.STARTED,
            limit=limit,
            files_requested=files_types,
            **additional_info,
        )

    def on_collected_details(
        self,
        file_name_collected_from_site,
        links_collected_from_site="FTP_ACSSES_LINK_MEANINGLESS",
        **additional_info,
    ):
        """report file details collected"""
        self._insert_an_update(
            ScraperStatus.COLLECTED,
            file_name_collected_from_site=file_name_collected_from_site,
            links_collected_from_site=links_collected_from_site,
            **additional_info,
        )

    def on_download_completed(self, **additional_info):
        """report file downloaded"""
        self._insert_an_update(ScraperStatus.DOWNLOADED, **additional_info)
        self._add_downloaded_files_to_list(**additional_info)

    def filter_already_downloaded(
        self, storage_path, files_names_to_scrape, filelist, by_function=lambda x: x
    ):
        """filter files already exists in long term memory or was downloaded before"""
        if self.collection_status:
            # filter according to database
            store_db = self.myclient[self.database]

            new_filelist = []
            for file in filelist:
                if not store_db["scraper_download"].find_one(
                    {"file_name": by_function(file)}
                ):
                    new_filelist.append(file)
                else:
                    Logger.info(
                        f"filtered file {file} since it already "
                        "was downloaded and extracted"
                    )
            return new_filelist

        # filter according to disk
        exits_on_disk = os.listdir(storage_path)

        if files_names_to_scrape:
            # delete what ever to retry
            for file in exits_on_disk:
                if file.split(".")[0] in files_names_to_scrape:
                    os.remove(os.path.join(storage_path,file))

            # find only the files we would like to download
            filelist = list(filter(lambda x: by_function(x) in files_names_to_scrape, filelist))

        return list(filter(lambda x: by_function(x) not in exits_on_disk, filelist))

    def _add_downloaded_files_to_list(self, results, **_):
        if self.collection_status:
            when = datetime.datetime.now()
            store_db = self.myclient[self.database]
            for res in results:
                if res["downloaded"] and res["extract_succefully"]:
                    store_db["scraper_download"].insert_one(
                        {"file_name": res["file_name"], "when": when}
                    )

    def on_scrape_completed(self, folder_name):
        """report when scarpe is completed"""
        self._insert_an_update(
            ScraperStatus.ESTIMATED_SIZE, folder_size=log_folder_details(folder_name)
        )

    def _insert_an_update(self, status, **additional_info):
        if self.collection_status:
            try:
                store_db = self.myclient[self.database]
                store_db["scraper_status"].insert_one(
                    {
                        "status": status,
                        "when": datetime.datetime.now(),
                        **additional_info,
                    }
                )

            except ServerSelectionTimeoutError:
                self.collection_status = False
