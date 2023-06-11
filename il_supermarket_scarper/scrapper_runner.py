import os

from multiprocessing import Pool

from .scrappers_factory import ScraperFactory
from .utils import Logger, summerize_dump_folder_contant, clean_dump_folder


class MainScrapperRunner:
    """a main scraper to execute all scraping"""

    def __init__(
        self,
        size_estimation_mode=False,
        enabled_scrapers=None,
        dump_folder_name=None,
        multiprocessing=5,
        lookup_in_db=False,
    ):
        assert isinstance(enabled_scrapers, list) or enabled_scrapers is None

        env_size_estimation_mode = os.getenv("SE_MODE", None)
        if env_size_estimation_mode:
            Logger.info(
                f"Setting size estimation mode from enviroment. value={env_size_estimation_mode}"
            )
            self.size_estimation_mode = bool(env_size_estimation_mode == "True")
        else:
            self.size_estimation_mode = size_estimation_mode
        Logger.info(f"size_estimation_mode: {self.size_estimation_mode}")

        if not enabled_scrapers:
            enabled_scrapers = ScraperFactory.all_scrapers_name()

        self.enabled_scrapers = enabled_scrapers
        Logger.info(f"Enabled scrapers: {self.enabled_scrapers}")
        self.dump_folder_name = dump_folder_name
        self.multiprocessing = multiprocessing
        self.lookup_in_db = lookup_in_db

    def run(self, limit=None, files_types=None, only_latest=False):
        """run the scraper"""
        Logger.info(f"Limit is {limit}")
        Logger.info(f"files_types is {files_types}")
        Logger.info("Start scraping all supermarkets.")

        with Pool(self.multiprocessing) as pool:
            result = pool.map(
                self.scrape_one_wrap,
                list(
                    map(
                        lambda chainScrapperClass: (
                            chainScrapperClass,
                            {
                                "limit": limit,
                                "files_types": files_types,
                                "only_latest": only_latest,
                            },
                        ),
                        self.enabled_scrapers,
                    )
                ),
            )

        Logger.info("Done scraping all supermarkets.")

        return result

    def scrape_one_wrap(self, arg):
        """scrape one warper"""
        args, kwargs = arg
        return self.scrape_one(args, **kwargs)

    def scrape_one(
        self,
        chain_scrapper_class,
        limit=None,
        files_types=None,
        store_id=None,
        only_latest=False,
    ):
        """scrape one"""
        chain_scrapper_constractor = ScraperFactory.get(chain_scrapper_class)
        Logger.info(f"Starting scrapper {chain_scrapper_constractor}")
        scraper = chain_scrapper_constractor(folder_name=self.dump_folder_name)
        chain_name = scraper.get_chain_name()

        Logger.info(f"scraping {chain_name}")
        if self.lookup_in_db:
            scraper.enable_collection_status()
        scraper.scrape(
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            only_latest=only_latest,
            files_names_to_scrape=None,
        )
        Logger.info(f"done scraping {chain_name}")

        folder_with_files = scraper.get_storage_path()
        if self.size_estimation_mode:
            Logger.info(f"Summrize test data for {chain_name}")
            summerize_dump_folder_contant(folder_with_files)

            Logger.info(f"Cleaning dump folder for {chain_name}")
            clean_dump_folder(folder_with_files)
        return folder_with_files
