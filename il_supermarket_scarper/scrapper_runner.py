import os

from distutils.util import strtobool

from .utils.status import get_all_listed_scarpers_class_names,get_scraper_by_class
from .utils import Logger,summerize_dump_folder_contant,clean_dump_folder

class ScrapperRunner:
    
    def __init__(self,size_estimation_mode=False,enabled_scrapers=None,dump_folder_name=None) -> None:
        assert type(enabled_scrapers) == list or enabled_scrapers == None
        self.size_estimation_mode = size_estimation_mode or strtobool(os.getenv("SE_MODE","False"))
        Logger.info("size_estimation_mode: {}".format(self.size_estimation_mode))

        if not enabled_scrapers:
            enabled_scrapers = get_all_listed_scarpers_class_names()

        self.enabled_scrapers = enabled_scrapers
        Logger.info("Enabled scrapers: {}".format(self.enabled_scrapers))
        self.dump_folder_name = dump_folder_name

        
    def run(self,limit=None,files_types=None): 
        Logger.info("Limit is {}".format(limit))
        Logger.info("files_types is {}".format(files_types))         
        
        result = list()
        for chainScrapperClass in self.enabled_scrapers:
            chainScrapper = get_scraper_by_class(chainScrapperClass)
            Logger.info("Starting scrapper {}".format(chainScrapper.__name__))
            scraper = chainScrapper(folder_name=self.dump_folder_name)
            chain_name = scraper.get_chain_name()

            Logger.info(f"scraping {chain_name}") 
            scraper.scrape(limit=limit,files_types=files_types)
            Logger.info(f"done scraping {chain_name}") 
            
            if self.size_estimation_mode:
                Logger.info("Summrize test data for {}".format(chain_name))
                summerize_dump_folder_contant()

                Logger.info("Cleaning dump folder for {}".format(chain_name))
                clean_dump_folder()
            else:
                result.append(scraper.get_storage_path())
        
        return result

