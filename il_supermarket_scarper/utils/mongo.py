import datetime
import os
import uuid


class DataBase:
    collection_status = False
    URL = os.environ.get('XML_STORE_PATH',"localhost:27017")
    myclient = None
    if collection_status:
        import pymongo
        myclient = pymongo.MongoClient(f"mongodb://{URL}/")
    

    
class ScrapingStatus(DataBase):
    CREATED = "CREATED"
    DOWNLOADED = "DOWNLOADED"
    FAILURE = "FAILURE"
    SKIPPED = "SKIPPED"


    # @staticmethod
    # def on_created(folder_name,filename,url,**additional_info):
    #     ScrapingStatus._insert_an_update(folder_name,filename,url,ScrapingStatus.CREATED,**additional_info)

    # @staticmethod
    # def on_download(folder_name,filename,url,**additional_info):
    #     ScrapingStatus._insert_an_update(folder_name,filename,url,ScrapingStatus.DOWNLOADED,**additional_info)

    # @staticmethod
    # def on_failure(folder_name,filename,url,**additional_info):
    #     ScrapingStatus._insert_an_update(folder_name,filename,url,ScrapingStatus.FAILURE,**additional_info)

    # @staticmethod
    # def on_skipped(folder_name,filename,url,**additional_info):
    #     ScrapingStatus._insert_an_update(folder_name,filename,url,ScrapingStatus.SKIPPED,**additional_info)


    # @staticmethod
    # def _insert_an_update(folder_name,filename,url,status,**additional_info):
    #     store_db = self.myclient[folder_name]
    #     store_db["scrapings"].insert_one({
    #         "date": datetime.datetime.now(),
    #         "status": status,
    #         "filename": filename,
    #         "url": url,
    #         "additional_info": additional_info
    #     })



class ScraperStatus(DataBase):
    STARTED = "started"
    COLLECTED = "collected"
    DOWNLOADED = "downloaded"
    ESTIMATED_SIZE = "estimated_size"

    def __init__(self,database) -> None:
        self.database = database.replace(" ","_").lower()
        self.instance_id = uuid.uuid4().hex

    def on_scraping_start(self,**additional_info):
        self._insert_an_update(ScraperStatus.STARTED,**additional_info)

    def on_collected_details(self,**additional_info):
        self._insert_an_update(ScraperStatus.COLLECTED,**additional_info)

    def on_download_completed(self,**additional_info):   
        self._insert_an_update(ScraperStatus.DOWNLOADED,**additional_info)

    def on_scrape_completed(self,folder_name):
        from il_supermarket_scarper.utils.status import log_folder_details
        self._insert_an_update(ScraperStatus.ESTIMATED_SIZE,folder_size=log_folder_details(folder_name))
    
    def _insert_an_update(self,status,**additional_info):
        if self.collection_status:
            store_db = self.myclient[self.database]
            store_db["scraper_status"].update_one(
                {"instance_id":self.instance_id},
                {"$set":{
                status: datetime.datetime.now(),
                **additional_info
                 }
                 },
            upsert=True)