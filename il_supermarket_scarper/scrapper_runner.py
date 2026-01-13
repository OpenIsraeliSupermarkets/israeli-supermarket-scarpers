import os
import datetime
import time
from multiprocessing import Pool

from .scrappers_factory import ScraperFactory
from .utils import (
    Logger,
    DumpFolderNames,
    DiskFileOutput,
    QueueFileOutput,
    InMemoryQueueHandler,
    KafkaQueueHandler,
    FilterState,
    _now,
)


class MainScrapperRunner:
    """a main scraper to execute all scraping"""

    def __init__(
        self,
        enabled_scrapers=None,
        timeout_in_seconds=60 * 30,
        multiprocessing=5,
        output_configuration=None,
        status_configuration=None,
    ):
        assert isinstance(enabled_scrapers, list) or enabled_scrapers is None

        if not enabled_scrapers:
            enabled_scrapers = ScraperFactory.all_scrapers_name()

        self.enabled_scrapers = enabled_scrapers
        Logger.info(f"Enabled scrapers: {self.enabled_scrapers}")
        self.multiprocessing = multiprocessing
        self.timeout_in_seconds = timeout_in_seconds
        self.file_output_config = output_configuration or {
            "output_mode": "disk",
            "base_storage_path": "dumps",
        }
        self.status_config = status_configuration or {
            "database_type": "json",
            "base_path": "dumps/status",
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

    def _create_status_database_for_scraper(self, scraper_name, config):
        """Create a status database instance for a specific scraper based on config."""
        from .utils.databases import JsonDataBase, MongoDataBase

        target_folder = DumpFolderNames[scraper_name].value
        database_name = target_folder

        # Use default config if None
        if config is None:
            config = {
                "database_type": "json",
                "base_path": "dumps/status",
            }

        database_type = config.get("database_type", "json")

        if database_type == "json":
            # JSON file database
            base_path = config.get("base_path", "dumps/status")
            return JsonDataBase(
                database_name, base_path=os.path.join(base_path, target_folder)
            )

        elif database_type == "mongo":
            # MongoDB database
            db = MongoDataBase(database_name)
            db.create_connection()
            return db

        else:
            raise ValueError(
                f"Unknown database_type: {database_type}. Must be 'json' or 'mongo'"
            )

    def run(
        self,
        limit=None,
        files_types=None,
        when_date=False,
        min_size=None,
        max_size=None,
        single_pass=True,
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
                            "min_size": min_size,
                            "max_size": max_size,
                            "file_output_config": self.file_output_config,
                            "status_database_config": self.status_config,
                            "single_pass": single_pass,
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
            return loop.run_until_complete(
                self.scrape_one(chainScrapperClass, **kwargs)
            )
        finally:
            loop.close()

    async def scrape_one(
        self,
        chain_scrapper_class,
        limit=None,
        single_pass=False,
        files_types=None,
        store_id=None,
        when_date=None,
        min_size=None,
        max_size=None,
        file_output_config=None,
        status_database_config=None,
    ):
        """scrape one"""

        chain_scrapper_constractor = ScraperFactory.get(chain_scrapper_class)
        Logger.info(f"Starting scrapper {chain_scrapper_constractor}")

        # Create file_output for this specific scraper based on its folder name
        file_output = self._create_file_output_for_scraper(
            chain_scrapper_class, file_output_config
        )

        # Create status output for this specific scraper
        status_database = self._create_status_database_for_scraper(
            chain_scrapper_class, status_database_config
        )

        # Create scraper with both file_output and status_database
        scraper = chain_scrapper_constractor(
            file_output=file_output, status_database=status_database
        )

        chain_name = scraper.get_chain_name()

        Logger.info(f"scraping {chain_name}")

        # Track state across multiple runs
        state = FilterState()
        run_count = 0
        initial_when_date = when_date

        # Loop until one of the exit conditions is met
        while True:
            run_count += 1
            Logger.info(f"[{chain_name}] Starting run #{run_count}")

            # Run the scraper
            collected_now_count = 0
            async for _ in scraper.scrape(
                state=state,
                limit=limit,
                files_types=files_types,
                store_id=store_id,
                when_date=when_date,
                files_names_to_scrape=None,
                filter_null=False,
                filter_zero=False,
                min_size=min_size,
                max_size=max_size,
            ):
                collected_now_count += 1

            Logger.info(
                f"[{chain_name}] Run #{run_count} completed. "
                f"Files found: {collected_now_count}, "
                f"Total files: {state.file_pass_limit}"
            )

            # Check exit conditions
            should_exit = False
            exit_reason = None

            # Condition 1: Limit reached
            if limit is not None and state.file_pass_limit >= limit:
                should_exit = True
                exit_reason = f"limit reached ({state.file_pass_limit}/{limit})"

            # Condition 2: Single pass completed
            elif single_pass:
                should_exit = True
                exit_reason = "single pass completed"

            # Condition 3: when_date provided, day has passed, and no new files found
            elif initial_when_date is not None and isinstance(
                initial_when_date, datetime.datetime
            ):
                current_date = _now().date()
                when_date_date = initial_when_date.date()

                # Check if the day has passed
                if current_date > when_date_date:
                    # If no files were found in this run, exit
                    if collected_now_count == 0:
                        should_exit = True
                        exit_reason = (
                            f"day has passed ({when_date_date} -> {current_date}) "
                            f"and no additional files found"
                        )
                    else:
                        # Day passed but files were found, continue
                        Logger.info(
                            f"[{chain_name}] Day has passed but found {collected_now_count} "
                            f"files, continuing..."
                        )

            if should_exit:
                Logger.info(f"[{chain_name}] Exiting loop: {exit_reason}")
                break
            else:
                Logger.info(
                    f"[{chain_name}] Sleeping for {self.timeout_in_seconds} seconds"
                )
                time.sleep(self.timeout_in_seconds)

            # If we're continuing, log that we'll run again
            Logger.info(f"[{chain_name}] Continuing to next run...")

        Logger.info(f"done scraping {chain_name}")
