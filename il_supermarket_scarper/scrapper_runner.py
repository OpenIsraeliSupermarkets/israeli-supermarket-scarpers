import os

from distutils.util import strtobool
from multiprocessing import Pool

from .utils.status import get_all_listed_scarpers_class_names, get_scraper_by_class
from .utils import Logger, summerize_dump_folder_contant, clean_dump_folder


class MainScrapperRunner:
    def __init__(
        self,
        size_estimation_mode=False,
        enabled_scrapers=None,
        dump_folder_name=None,
        multiprocessing=5,
        lookup_in_db=False,
    ):
        assert type(enabled_scrapers) == list or enabled_scrapers == None

        env_size_estimation_mode = os.getenv("SE_MODE", None)
        if env_size_estimation_mode:
            Logger.info(
                f"Setting size estimation mode from enviroment. value={env_size_estimation_mode}"
            )
            self.size_estimation_mode = bool(strtobool(env_size_estimation_mode))
        else:
            self.size_estimation_mode = size_estimation_mode
        Logger.info("size_estimation_mode: {}".format(self.size_estimation_mode))

        if not enabled_scrapers:
            enabled_scrapers = get_all_listed_scarpers_class_names()

        self.enabled_scrapers = enabled_scrapers
        Logger.info("Enabled scrapers: {}".format(self.enabled_scrapers))
        self.dump_folder_name = dump_folder_name
        self.multiprocessing = multiprocessing
        self.lookup_in_db = lookup_in_db

    def run(self, limit=None, files_types=None):
        Logger.info("Limit is {}".format(limit))
        Logger.info("files_types is {}".format(files_types))
        Logger.info("Start scraping all supermarkets.")

        with Pool(self.multiprocessing) as p:
            result = p.map(
                self.scrape_one_wrap,
                list(
                    map(
                        lambda chainScrapperClass: (
                            chainScrapperClass,
                            {"limit": limit, "files_types": files_types},
                        ),
                        self.enabled_scrapers,
                    )
                ),
            )

        Logger.info("Done scraping all supermarkets.")

        return result

    def scrape_one_wrap(self, arg):
        args, kwargs = arg
        return self.scrape_one(args, **kwargs)

    def scrape_one(self, chainScrapperClass, limit=None, files_types=None):
        chainScrapper = get_scraper_by_class(chainScrapperClass)
        Logger.info("Starting scrapper {}".format(chainScrapper.__name__))
        scraper = chainScrapper(folder_name=self.dump_folder_name)
        chain_name = scraper.get_chain_name()

        Logger.info(f"scraping {chain_name}")
        if self.lookup_in_db:
            scraper.enable_collection_status()
        scraper.scrape(limit=limit, files_types=files_types)
        Logger.info(f"done scraping {chain_name}")

        folder_with_files = scraper.get_storage_path()
        if self.size_estimation_mode:
            Logger.info("Summrize test data for {}".format(chain_name))
            summerize_dump_folder_contant(folder_with_files)

            Logger.info("Cleaning dump folder for {}".format(chain_name))
            clean_dump_folder(folder_with_files)
        return folder_with_files
