import datetime
import os
import uuid


class DataBase:

    def __init__(self,collection_status=False) -> None:
        self.myclient = None
        self.collection_status = collection_status
        try:
            if collection_status:
                import pymongo     
                url = os.environ.get('MONGO_URL',"localhost")
                port = os.environ.get('MONGO_PORT',"27017")
                self.myclient = pymongo.MongoClient(f"mongodb://{url}:{port}/")
                self.collection_status = True
        except Exception:
            collection_status = False
        

class ScraperStatus(DataBase):
    STARTED = "started"
    COLLECTED = "collected"
    DOWNLOADED = "downloaded"
    ESTIMATED_SIZE = "estimated_size"

    def __init__(self,database,collection_status=False) -> None:
        super().__init__(collection_status=collection_status)
        self.database = database.replace(" ","_").lower()
        self.instance_id = uuid.uuid4().hex

    def on_scraping_start(self,**additional_info):
        self._insert_an_update(ScraperStatus.STARTED,**additional_info)

    def on_collected_details(self,**additional_info):
        self._insert_an_update(ScraperStatus.COLLECTED,**additional_info)

    def on_download_completed(self,**additional_info):   
        self._insert_an_update(ScraperStatus.DOWNLOADED,**additional_info)
        self._add_downloaded_files_to_list(**additional_info)

    def filter_already_downloaded(self,storage_path,filelist,by=None):
        if self.collection_status:
            # filter according to database
            store_db = self.myclient[self.database]

            new_filelist = list()
            by_function = by if by else lambda x:x
            for file in filelist:
                if not store_db["scraper_download"].find_one({"file_name":by_function(file)}):
                    new_filelist.append(file)
            return new_filelist
        else:
            # filter according to disk
            exits_on_disk = os.listdir(storage_path)
            return list(filter(lambda x:x not in exits_on_disk,filelist))

    def _add_downloaded_files_to_list(self,results,**_):
        if self.collection_status:
            when = datetime.datetime.now()
            store_db = self.myclient[self.database]
            for res in results:
                if res['downloaded'] and res['extract_succefully']:        
                    store_db["scraper_download"].insert_one({
                        "file_name":res['file_name'],
                        "when":when
                    })

    def on_scrape_completed(self,folder_name):
        from il_supermarket_scarper.utils.status import log_folder_details
        self._insert_an_update(ScraperStatus.ESTIMATED_SIZE,folder_size=log_folder_details(folder_name))
    
    def _insert_an_update(self,status,**additional_info):
        if self.collection_status:
            store_db = self.myclient[self.database]
            store_db["scraper_status"].insert_one(
                {
                "status": status,
                "when":datetime.datetime.now(),
                **additional_info
                })