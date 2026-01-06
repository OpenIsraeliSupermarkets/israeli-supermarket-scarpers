import os
import asyncio

from multiprocessing import Pool

from .scrappers_factory import ScraperFactory
from .utils import (
    Logger,
    summerize_dump_folder_contant,
    clean_dump_folder,
    DumpFolderNames,
    DiskFileOutput,
    QueueFileOutput,
    InMemoryQueueHandler,
    KafkaQueueHandler,
)


class MainScrapperRunner:
    """a main scraper to execute all scraping"""

    def __init__(
        self,
        size_estimation_mode=False,
        enabled_scrapers=None,
        multiprocessing=5,
        lookup_in_db=True,
        output_configuration=None,
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
        self.multiprocessing = multiprocessing
        self.lookup_in_db = lookup_in_db
        self.file_output_config = output_configuration or {
            "output_mode": "disk",
            "base_storage_path": "dumps",
        }

    def _create_file_output_for_scraper(self, scraper_name, config):
        """Create a file_output instance for a specific scraper based on config."""
        target_folder = DumpFolderNames[scraper_name].value
        
        # Use default config if None
        if config is None:
            config = {
                "output_mode": "disk",
                "base_storage_path": "dumps",
            }
        
        if config.get("output_mode") == "disk":
            # Disk output mode
            base_path = config.get("base_storage_path", "dumps")
            return DiskFileOutput(storage_path=os.path.join(base_path, target_folder))

        elif config.get("output_mode") == "queue":
            # Queue output mode
            queue_type = config.get("queue_type", "memory")

            if queue_type == "memory":
                return QueueFileOutput(InMemoryQueueHandler(queue_name=target_folder))

            elif queue_type == "kafka":
                bootstrap_servers = config.get(
                    "kafka_bootstrap_servers", "localhost:9092"
                )
                return QueueFileOutput(
                    KafkaQueueHandler(
                        bootstrap_servers=bootstrap_servers, topic=target_folder
                    )
                )

    def run(
        self,
        limit=None,
        files_types=None,
        when_date=False,
        suppress_exception=False,
        min_size=None,
        max_size=None,
    ):
        """run the scraper"""
        Logger.info(f"Limit is {limit}")
        Logger.info(f"files_types is {files_types}")
        Logger.info(f"Start scraping {','.join(self.enabled_scrapers)}.")

        with Pool(self.multiprocessing) as pool:
            result = pool.starmap(
                self.scrape_one_wrap,
                [
                    (
                        chainScrapperClass,
                        {
                            "limit": limit,
                            "files_types": files_types,
                            "when_date": when_date,
                            "suppress_exception": False,
                            "min_size": min_size,
                            "max_size": max_size,
                            "file_output_config": self.file_output_config,
                        },
                    )
                    for chainScrapperClass in self.enabled_scrapers
                ],
            )

        Logger.info("Done scraping all supermarkets.")

        return result

    def scrape_one_wrap(self, chainScrapperClass, kwargs):
        """scrape one wrapper, each with its own event loop"""
        import asyncio
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.scrape_one(chainScrapperClass, **kwargs))
        finally:
            loop.close()

    async def scrape_one(
        self,
        chain_scrapper_class,
        limit=None,
        files_types=None,
        store_id=None,
        when_date=None,
        suppress_exception=False,
        min_size=None,
        max_size=None,
        file_output_config=None,
    ):
        """scrape one"""
        chain_scrapper_constractor = ScraperFactory.get(chain_scrapper_class)
        Logger.info(f"Starting scrapper {chain_scrapper_constractor}")

        # Create file_output for this specific scraper based on its folder name
        file_output = self._create_file_output_for_scraper(
            chain_scrapper_class, file_output_config
        )
        # Create scraper with file_output if provided
        scraper = chain_scrapper_constractor(file_output=file_output)

        chain_name = scraper.get_chain_name()

        Logger.info(f"scraping {chain_name}")
        if self.lookup_in_db:
            scraper.enable_collection_status()
            scraper.enable_aggregation_between_runs()

        async for _ in scraper.scrape(
            limit=limit,
            files_types=files_types,
            store_id=store_id,
            when_date=when_date,
            files_names_to_scrape=None,
            filter_null=False,
            filter_zero=False,
            suppress_exception=suppress_exception,
            min_size=min_size,
            max_size=max_size,
        ):
            pass
        Logger.info(f"done scraping {chain_name}")

        folder_with_files = scraper.get_storage_path()
        if self.size_estimation_mode:
            Logger.info(f"Summrize test data for {chain_name}")
            summerize_dump_folder_contant(folder_with_files)

            Logger.info(f"Cleaning dump folder for {chain_name}")
            clean_dump_folder(folder_with_files)
        return folder_with_files
